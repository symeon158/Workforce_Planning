import streamlit as st
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, PULP_CBC_CMD
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components   # <<< ΝΕΟ

st.set_page_config(layout="wide")


# ===================== ADVANCED HEADER =====================
def render_advanced_header(total_initial, effective_salary_cost, budget):
    # Safe fallbacks
    total_initial = total_initial or 0
    effective_salary_cost = effective_salary_cost or 0
    budget = budget or 0

    header_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
:root {{
  --primary: #0d6efd;
  --primary-dark: #0b5ed7;
  --accent: #22c55e;
  --bg-dark: #0f172a;
  --bg-light: #f9fafb;
  --text-main: #f9fafb;
  --text-muted: #cbd5f5;
}}

body {{
  margin: 0;
  padding: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

.wf-header-wrapper {{
  width: 100%;
  box-sizing: border-box;
  background: radial-gradient(circle at top left, #1d4ed8, #020617);
  color: var(--text-main);
  padding: 1.8rem 3rem 1.6rem 3rem;
  box-shadow: 0 14px 40px rgba(15, 23, 42, 0.55);
  border-bottom: 1px solid rgba(148, 163, 184, 0.35);
}}

.wf-header-grid {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}}

.wf-title-block {{
  flex: 2 1 260px;
}}

.wf-title {{
  font-size: 1.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin: 0 0 0.4rem 0;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}}

.wf-title-pill {{
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  padding: 0.18rem 0.6rem;
  border-radius: 999px;
  border: 1px solid rgba(248, 250, 252, 0.55);
  background: rgba(15, 23, 42, 0.35);
}}

.wf-subtitle {{
  font-size: 0.92rem;
  font-weight: 400;
  color: var(--text-muted);
  max-width: 520px;
  line-height: 1.4;
}}

.wf-badges {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.5rem;
}}

.wf-badge {{
  font-size: 0.7rem;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.7);
  background: rgba(15, 23, 42, 0.65);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}}

.wf-badge-dot {{
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.25);
}}

.wf-kpi-block {{
  flex: 1.4 1 260px;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  flex-wrap: wrap;
}}

.wf-kpi-card {{
  min-width: 130px;
  padding: 0.65rem 0.75rem;
  border-radius: 0.9rem;
  background: radial-gradient(circle at top left, rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.78));
  border: 1px solid rgba(148, 163, 184, 0.65);
}}

.wf-kpi-label {{
  font-size: 0.70rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--text-muted);
  margin-bottom: 0.15rem;
}}

.wf-kpi-value {{
  font-size: 1.08rem;
  font-weight: 600;
}}

.wf-kpi-caption {{
  font-size: 0.70rem;
  color: var(--text-muted);
  margin-top: 0.1rem;
}}

@media (max-width: 768px) {{
  .wf-header-wrapper {{
    padding: 1.5rem 1.5rem 1.3rem 1.5rem;
  }}
  .wf-kpi-block {{
    justify-content: flex-start;
  }}
}}
</style>
</head>
<body>
<div class="wf-header-wrapper">
  <div class="wf-header-grid">

    <div class="wf-title-block">
      <div class="wf-title">
        <span>Workforce Planning Optimization</span>
        <span class="wf-title-pill">HR · Operations · Finance</span>
      </div>
      <div class="wf-subtitle">
        Interactive PuLP-based optimization for workforce, overtime and budget allocation —
        tailored for monthly demand, service level targets and HR grade structure.
      </div>
      <div class="wf-badges">
        <span class="wf-badge">
          <span class="wf-badge-dot"></span>
          Live optimization
        </span>
        <span class="wf-badge">PuLP · Linear Programming</span>
        <span class="wf-badge">Streamlit · Plotly</span>
        <span class="wf-badge">Service rate control</span>
      </div>
    </div>

    <div class="wf-kpi-block">
      <div class="wf-kpi-card">
        <div class="wf-kpi-label">Initial headcount</div>
        <div class="wf-kpi-value">{total_initial:,}</div>
        <div class="wf-kpi-caption">Total employees across all grades</div>
      </div>
      <div class="wf-kpi-card">
        <div class="wf-kpi-label">Effective monthly salary</div>
        <div class="wf-kpi-value">{effective_salary_cost:,.0f}</div>
        <div class="wf-kpi-caption">Weighted average per FTE</div>
      </div>
      <div class="wf-kpi-card">
        <div class="wf-kpi-label">Budget envelope</div>
        <div class="wf-kpi-value">{int(budget):,}</div>
        <div class="wf-kpi-caption">Total allowed cost (excl. penalties)</div>
      </div>
    </div>

  </div>
</div>
</body>
</html>
"""
    # Εδώ ΔΕΝ χρησιμοποιούμε st.markdown
    components.html(header_html, height=260, scrolling=False)



# ===================== OPTIMIZER =====================
def solve_workforce_planning(
    months, hiring_cost, firing_cost, effective_salary_cost, penalty_cost,
    overtime_cost, initial_employees, maxh, maxf, overtime_rate,
    working_hours, demand, budget, service_rate
):
    problem = LpProblem("Workforce_Planning", LpMinimize)

    H = [LpVariable(f"H_{i}", lowBound=0, cat="Integer") for i in range(months)]
    F = [LpVariable(f"F_{i}", lowBound=0, cat="Integer") for i in range(months)]
    E = [LpVariable(f"E_{i}", lowBound=0, cat="Integer") for i in range(months)]
    O = [LpVariable(f"O_{i}", lowBound=0, cat="Integer") for i in range(months)]
    U = [LpVariable(f"U_{i}", lowBound=0, cat="Integer") for i in range(months)]

    problem += lpSum(
        H[i] * hiring_cost
        + F[i] * firing_cost
        + E[i] * effective_salary_cost
        + O[i] * overtime_cost
        + U[i] * penalty_cost
        for i in range(months)
    ), "Total_Cost"

    for i in range(months):
        if i == 0:
            problem += E[i] == initial_employees + H[i] - F[i], f"Initial_Balance_{i}"
        else:
            problem += E[i] == E[i - 1] + H[i] - F[i], f"Balance_{i}"

        problem += E[i] * working_hours + O[i] + U[i] >= demand[i] * service_rate, f"Demand_Cover_{i}"
        problem += H[i] <= maxh, f"Hiring_Capacity_{i}"
        problem += F[i] <= maxf, f"Firing_Capacity_{i}"
        problem += O[i] <= E[i] * overtime_rate, f"Overtime_Limit_{i}"
        problem += U[i] >= demand[i] - (E[i] * working_hours + O[i]), f"Unmet_Demand_{i}"

    total_cost_excl_penalty = lpSum(
        H[i] * hiring_cost + F[i] * firing_cost + E[i] * effective_salary_cost + O[i] * overtime_cost
        for i in range(months)
    )
    problem += total_cost_excl_penalty <= budget, "Budget_Constraint"

    problem.solve(PULP_CBC_CMD(msg=True))

    def safe_value(var):
        v = var.value()
        return int(v) if v is not None else 0

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
default_budget = int(total_initial * effective_salary_cost * int(months) + 150_000)
if use_auto_budget:
    budget = default_budget
    st.sidebar.markdown(f"**Auto-Calculated Budget:** {budget:,.0f}")
else:
    budget = st.sidebar.number_input("Manual Budget", min_value=0, value=int(default_budget), step=10_000)
st.sidebar.markdown(f"**Budget:** {int(budget):,.0f}")

service_rate = st.sidebar.slider("Service Rate", min_value=0.0, max_value=1.0, value=0.95)

# ==== HEADER ====
render_advanced_header(total_initial, effective_salary_cost, budget)

# -------- Demand Inputs --------
st.sidebar.header("Monthly Demand (hours)")

M = int(months)
WH = int(working_hours)
capacity_default = int(total_initial * WH)

auto_update_demands = st.sidebar.checkbox("Auto-update demands when capacity changes", value=True)

current_sig = (M, int(total_initial), WH)
if "demand_sig" not in st.session_state:
    st.session_state["demand_sig"] = None

existing_keys = [k for k in st.session_state.keys() if k.startswith("demand_")]
existing_idx = sorted([int(k.split("_")[1]) for k in existing_keys if k.split("_")[1].isdigit()])
for i in existing_idx:
    if i >= M:
        key_to_drop = f"demand_{i}"
        if key_to_drop in st.session_state:
            del st.session_state[key_to_drop]

if ("demand_initialized" not in st.session_state) or (auto_update_demands and st.session_state["demand_sig"] != current_sig):
    for i in range(M):
        st.session_state[f"demand_{i}"] = capacity_default
    st.session_state["demand_initialized"] = True
    st.session_state["demand_sig"] = current_sig

if st.sidebar.button("Reset all monthly demands to capacity"):
    for i in range(M):
        st.session_state[f"demand_{i}"] = int(total_initial * WH)

demand = []
for i in range(M):
    key = f"demand_{i}"
    if key not in st.session_state:
        st.session_state[key] = capacity_default

    d = st.sidebar.number_input(
        f"Demand for Month {i+1}",
        min_value=0,
        step=100,
        key=key
    )
    demand.append(int(d))

# ===================== RUN =====================
if st.button("Optimize"):
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

    df = pd.DataFrame(results["Details"])
    st.write("Results in a Tabular Form:")
    st.dataframe(df, use_container_width=True)

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df['Month'], y=df['Hired'], name='Hired'))
    fig1.add_trace(go.Bar(x=df['Month'], y=df['Fired'], name='Fired'))
    fig1.update_layout(
        barmode='group',
        xaxis_title='Month',
        yaxis_title='Count',
        title='Hired vs Fired Employees per Month'
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df['Month'], y=df['Overtime (hours)'], name='Overtime'))
    fig2.add_trace(go.Bar(x=df['Month'], y=df['Unmet Demand (hours)'], name='Unmet Demand'))
    fig2.update_layout(
        barmode='group',
        xaxis_title='Month',
        yaxis_title='Hours',
        title='Overtime vs Unmet Demand per Month'
    )
    st.plotly_chart(fig2, use_container_width=True)

    df['Total Workforce Capacity'] = df['Employees'] * WH + df['Overtime (hours)']
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df['Month'],
        y=df['Total Workforce Capacity'],
        mode='lines+markers',
        name='Total Workforce Capacity'
    ))
    fig3.add_trace(go.Scatter(
        x=df['Month'],
        y=df['Demand (hours)'],
        mode='lines+markers',
        name='Demand'
    ))
    fig3.update_layout(
        xaxis_title='Month',
        yaxis_title='Hours',
        title='Total Workforce Capacity vs Demand',
        xaxis=dict(tickmode='linear', dtick=1)
    )
    st.plotly_chart(fig3, use_container_width=True)

    hiring_total_cost = int(df['Hired'].sum()) * int(hiring_cost)
    firing_total_cost = int(df['Fired'].sum()) * int(firing_cost)
    salary_total_cost = int(df['Employees'].sum()) * float(effective_salary_cost)
    overtime_total_cost = int(df['Overtime (hours)'].sum()) * int(overtime_cost)
    penalty_total_cost = int(df['Unmet Demand (hours)'].sum()) * int(penalty_cost)

    costs = [
        hiring_total_cost,
        firing_total_cost,
        salary_total_cost,
        overtime_total_cost,
        penalty_total_cost
    ]
    labels = ['Hiring Cost', 'Firing Cost', 'Salary Cost', 'Overtime Cost', 'Penalty Cost']

    fig4 = go.Figure(data=[go.Pie(labels=labels, values=costs, textinfo='percent+label')])
    fig4.update_layout(title='Cost Distribution')
    st.plotly_chart(fig4, use_container_width=True)



