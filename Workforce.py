import streamlit as st
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, PULP_CBC_CMD
import pandas as pd
import plotly.graph_objects as go

# ===================== OPTIMIZER =====================
def solve_workforce_planning(
    months, hiring_cost, firing_cost, effective_salary_cost, penalty_cost,
    overtime_cost, initial_employees, maxh, maxf, overtime_rate,
    working_hours, demand, budget, service_rate
):
    """
    Solve the workforce planning optimization model using an effective salary cost.
    """
    problem = LpProblem("Workforce_Planning", LpMinimize)

    # Decision variables
    H = [LpVariable(f"H_{i}", lowBound=0, cat="Integer") for i in range(months)]
    F = [LpVariable(f"F_{i}", lowBound=0, cat="Integer") for i in range(months)]
    E = [LpVariable(f"E_{i}", lowBound=0, cat="Integer") for i in range(months)]
    O = [LpVariable(f"O_{i}", lowBound=0, cat="Integer") for i in range(months)]
    U = [LpVariable(f"U_{i}", lowBound=0, cat="Integer") for i in range(months)]

    # Objective
    problem += lpSum(
        H[i] * hiring_cost
        + F[i] * firing_cost
        + E[i] * effective_salary_cost
        + O[i] * overtime_cost
        + U[i] * penalty_cost
        for i in range(months)
    ), "Total_Cost"

    # Constraints
    for i in range(months):
        # Workforce balance
        if i == 0:
            problem += E[i] == initial_employees + H[i] - F[i], f"Initial_Balance_{i}"
        else:
            problem += E[i] == E[i - 1] + H[i] - F[i], f"Balance_{i}"

        # Capacity vs demand (service level applied on demand side)
        problem += E[i] * working_hours + O[i] + U[i] >= demand[i] * service_rate, f"Demand_Cover_{i}"

        # Hiring/Firing capacity
        problem += H[i] <= maxh, f"Hiring_Capacity_{i}"
        problem += F[i] <= maxf, f"Firing_Capacity_{i}"

        # Overtime limit per employee
        problem += O[i] <= E[i] * overtime_rate, f"Overtime_Limit_{i}"

        # Unmet demand must cover any shortfall
        problem += U[i] >= demand[i] - (E[i] * working_hours + O[i]), f"Unmet_Demand_{i}"

    # Budget (excluding penalty)
    total_cost_excl_penalty = lpSum(
        H[i] * hiring_cost + F[i] * firing_cost + E[i] * effective_salary_cost + O[i] * overtime_cost
        for i in range(months)
    )
    problem += total_cost_excl_penalty <= budget, "Budget_Constraint"

    # Solve
    problem.solve(PULP_CBC_CMD(msg=True))

    def safe_value(var):
        v = var.value()
        return int(v) if v is not None else 0

    # Remove penalty from reported "Total Cost" if you want only controllable costs
    objective_penalty = sum(safe_value(U[i]) * penalty_cost for i in range(months))
    total_cost_reported = (problem.objective.value() or 0) - objective_penalty

    results = {
        "Status": LpStatus.get(problem.status, str(problem.status)),
        "Total Cost": total_cost_reported,
        "Details": []
    }

    for i in range(months):
        results["Details"].append({
            "Month": i + 1,
            "Demand (hours)": int(demand[i]),
            "Hired": safe_value(H[i]),
            "Fired": safe_value(F[i]),
            "Employees": safe_value(E[i]),
            "Overtime (hours)": safe_value(O[i]),
            "Unmet Demand (hours)": safe_value(U[i]),
        })

    return results


# ===================== UI =====================
st.markdown("""
    <style>
        .clean-title {
            font-size: 36px;
            font-weight: 600;
            color: #1f2937;
            text-align: center;
            padding: 20px 0 10px 0;
            border-bottom: 2px solid #0d6efd;
            margin-bottom: 30px;
        }
    </style>
    <div class="clean-title">Workforce Planning Optimization Dashboard</div>
""", unsafe_allow_html=True)

# -------- Grade Inputs --------
st.sidebar.header("Grade Settings")
num_grades = st.sidebar.number_input("Number of Grades", min_value=1, value=1, step=1)
grade_data = []
for i in range(int(num_grades)):
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        grade_name = st.text_input(f"Grade {i+1} Name", value=f"Grade {i+1}", key=f"grade_name_{i}")
    with col2:
        count = st.number_input(f"Count for {grade_name}", min_value=0, value=0, key=f"grade_count_{i}")
    with col3:
        salary = st.number_input(f"Salary for {grade_name}", min_value=0, value=0, key=f"grade_salary_{i}")
    grade_data.append((grade_name, count, salary))

# Compute total initial employees & effective salary cost
if grade_data:
    total_initial = int(sum(count for (_, count, _) in grade_data))
    effective_salary_cost = (
        (sum(count * salary for (_, count, salary) in grade_data) / total_initial)
        if total_initial > 0 else 0
    )
else:
    total_initial = 0
    effective_salary_cost = 0

st.sidebar.markdown(f"**Total Initial Employees (from grades):** {total_initial}")
st.sidebar.markdown(f"**Effective Salary Cost:** {effective_salary_cost:,.2f}")

# -------- Other Inputs --------
st.sidebar.header("Other Input Parameters")
months = st.sidebar.number_input("Number of Months", min_value=1, max_value=24, value=12, step=1)
hiring_cost = st.sidebar.number_input("Hiring Cost", value=1000, step=100)
firing_cost = st.sidebar.number_input("Firing Cost", value=1000, step=100)
penalty_cost = st.sidebar.number_input("Penalty for Unmet Demand", value=100)
overtime_cost = st.sidebar.number_input("Overtime Cost", value=75, step=10)

initial_employees = total_initial
maxh = st.sidebar.number_input("Maximum Hiring per Month", min_value=1, value=10)
maxf = st.sidebar.number_input("Maximum Firing per Month", min_value=1, value=5)
overtime_rate = st.sidebar.number_input("Overtime Hours per Employee", min_value=1, value=10)
working_hours = st.sidebar.number_input("Working Hours per Employee per Month", min_value=1, value=166)

use_auto_budget = st.sidebar.checkbox("Auto-calculate Budget", value=True)
# Compute default budget with current inputs
default_budget = int(total_initial * effective_salary_cost * int(months) + 150_000)
if use_auto_budget:
    budget = default_budget
    st.sidebar.markdown(f"**Auto-Calculated Budget:** {budget:,.0f}")
else:
    budget = st.sidebar.number_input("Manual Budget", min_value=0, value=int(default_budget), step=10_000)
st.sidebar.markdown(f"**Budget:** {int(budget):,.0f}")

service_rate = st.sidebar.slider("Service Rate", min_value=0.0, max_value=1.0, value=0.95)

# -------- Demand Inputs (robust defaults + state) --------
st.sidebar.header("Monthly Demand (hours)")

M = int(months)
WH = int(working_hours)
capacity_default = int(total_initial * WH)

# allow auto-update of defaults when key inputs change
auto_update_demands = st.sidebar.checkbox("Auto-update demands when capacity changes", value=True)

# a signature that triggers re-seed when changes
current_sig = (M, int(total_initial), WH)
if "demand_sig" not in st.session_state:
    st.session_state["demand_sig"] = None

# ensure demand_* keys match current months (drop excess)
existing_keys = [k for k in st.session_state.keys() if k.startswith("demand_")]
existing_idx = sorted([int(k.split("_")[1]) for k in existing_keys if k.split("_")[1].isdigit()])
for i in range(M, len(existing_idx)):
    key_to_drop = f"demand_{i}"
    if key_to_drop in st.session_state:
        del st.session_state[key_to_drop]

# seed (or reseed) defaults
if ("demand_initialized" not in st.session_state) or (auto_update_demands and st.session_state["demand_sig"] != current_sig):
    for i in range(M):
        st.session_state[f"demand_{i}"] = capacity_default
    st.session_state["demand_initialized"] = True
    st.session_state["demand_sig"] = current_sig

# manual reset
if st.sidebar.button("Reset all monthly demands to capacity"):
    for i in range(M):
        st.session_state[f"demand_{i}"] = int(total_initial * WH)

# render widgets (now values are already in state)
demand = []
for i in range(M):
    key = f"demand_{i}"
    if key not in st.session_state:
        st.session_state[key] = capacity_default
    d = st.sidebar.number_input(
        f"Demand for Month {i+1}",
        min_value=0,
        value=int(st.session_state[key]),
        step=100,
        key=key
    )
    demand.append(int(d))

# ===================== RUN =====================
if st.button("Optimize"):
    # ---- Guardrails before solve ----
    try:
        demand = [int(x) for x in demand]
    except Exception:
        demand = [int(x or 0) for x in demand]

    _required = {
        "months": M,
        "hiring_cost": hiring_cost,
        "firing_cost": firing_cost,
        "effective_salary_cost": effective_salary_cost,
        "penalty_cost": penalty_cost,
        "overtime_cost": overtime_cost,
        "initial_employees": initial_employees,
        "maxh": maxh,
        "maxf": maxf,
        "overtime_rate": overtime_rate,
        "working_hours": WH,
        "budget": budget,
        "service_rate": service_rate,
    }

    missing = [k for k, v in _required.items() if v is None]
    if len(demand) != M:
        missing.append(f"demand_len({len(demand)} != {M})")
    if missing:
        st.error(f"Internal setup error. Missing/invalid: {', '.join(map(str, missing))}")
        st.stop()

    with st.spinner("Solving the optimization model..."):
        try:
            results = solve_workforce_planning(
                M, int(hiring_cost), int(firing_cost), float(effective_salary_cost), int(penalty_cost),
                int(overtime_cost), int(initial_employees), int(maxh), int(maxf), int(overtime_rate),
                WH, demand, int(budget), float(service_rate)
            )
        except Exception as e:
            st.exception(e)
            st.stop()

    st.subheader("Optimization Results")
    st.write(f"Status: **{results['Status']}**")
    if results['Status'] == 'Optimal':
        st.success("Optimal solution found.")
    else:
        st.warning("Non-optimal solution or infeasible — review inputs/constraints.")

    st.write(f"Total Cost (excl. penalties): **{int(results['Total Cost']):,}**")

    # Variance vs budget
    total_cost_value = results['Total Cost']
    variance = int(budget) - (int(total_cost_value) if total_cost_value is not None else 0)
    percentage_variance = (variance / int(budget) * 100) if int(budget) > 0 else 0.0

    if variance >= 0:
        card_color = "#28a745"
        icon = "✅"
        variance_text = "Under Budget"
    else:
        card_color = "#dc3545"
        icon = "⚠️"
        variance_text = "Over Budget"

    st.markdown(f"""
    <div style="background-color: {card_color}; padding: 15px; border-radius: 5px; color: white; text-align: center;">
        <h2>{icon} {variance_text}</h2>
        <p style="font-size: 20px;">Variance: {variance:,.0f} units</p>
        <p style="font-size: 16px;">({percentage_variance:.2f}%)</p>
    </div>
    """, unsafe_allow_html=True)

    # Table
    df = pd.DataFrame(results["Details"])
    st.write("Results in a Tabular Form:")
    st.dataframe(df, use_container_width=True)

    # Charts
    # 1) Hired vs Fired
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df['Month'], y=df['Hired'], name='Hired'))
    fig1.add_trace(go.Bar(x=df['Month'], y=df['Fired'], name='Fired'))
    fig1.update_layout(barmode='group', xaxis_title='Month', yaxis_title='Count',
                       title='Hired vs Fired Employees per Month')
    st.plotly_chart(fig1, use_container_width=True)

    # 2) Overtime vs Unmet Demand
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df['Month'], y=df['Overtime (hours)'], name='Overtime'))
    fig2.add_trace(go.Bar(x=df['Month'], y=df['Unmet Demand (hours)'], name='Unmet Demand'))
    fig2.update_layout(barmode='group', xaxis_title='Month', yaxis_title='Hours',
                       title='Overtime vs Unmet Demand per Month')
    st.plotly_chart(fig2, use_container_width=True)

    # 3) Total Workforce Capacity vs Demand
    df['Total Workforce Capacity'] = df['Employees'] * WH + df['Overtime (hours)']
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df['Month'], y=df['Total Workforce Capacity'], mode='lines+markers',
                              name='Total Workforce Capacity'))
    fig3.add_trace(go.Scatter(x=df['Month'], y=df['Demand (hours)'], mode='lines+markers',
                              name='Demand'))
    fig3.update_layout(xaxis_title='Month', yaxis_title='Hours',
                       title='Total Workforce Capacity vs Demand',
                       xaxis=dict(tickmode='linear', dtick=1))
    st.plotly_chart(fig3, use_container_width=True)

    # 4) Cost Distribution
    hiring_total_cost = int(df['Hired'].sum()) * int(hiring_cost)
    firing_total_cost = int(df['Fired'].sum()) * int(firing_cost)
    salary_total_cost = int(df['Employees'].sum()) * float(effective_salary_cost)
    overtime_total_cost = int(df['Overtime (hours)'].sum()) * int(overtime_cost)
    penalty_total_cost = int(df['Unmet Demand (hours)'].sum()) * int(penalty_cost)

    costs = [hiring_total_cost, firing_total_cost, salary_total_cost,
             overtime_total_cost, penalty_total_cost]
    labels = ['Hiring Cost', 'Firing Cost', 'Salary Cost', 'Overtime Cost', 'Penalty Cost']

    fig4 = go.Figure(data=[go.Pie(labels=labels, values=costs, textinfo='percent+label')])
    fig4.update_layout(title='Cost Distribution')
    st.plotly_chart(fig4, use_container_width=True)
