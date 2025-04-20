import streamlit as st
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, PULP_CBC_CMD
import pandas as pd
import plotly.graph_objects as go

def solve_workforce_planning(months, hiring_cost, firing_cost, effective_salary_cost, penalty_cost,
                              overtime_cost, initial_employees, maxh, maxf, overtime_rate,
                              working_hours, demand, budget, service_rate):
    """
    Solve the workforce planning optimization model using an effective salary cost.
    """
    # Define the optimization problem
    problem = LpProblem("Workforce_Planning", LpMinimize)

    # Decision variables for each month:
    # H: Hired, F: Fired, E: Employees (end of period), O: Overtime (hours), U: Unmet demand (hours)
    H = [LpVariable(f"H_{i}", lowBound=0, cat='Integer') for i in range(months)]
    F = [LpVariable(f"F_{i}", lowBound=0, cat='Integer') for i in range(months)]
    E = [LpVariable(f"E_{i}", lowBound=0, cat='Integer') for i in range(months)]
    O = [LpVariable(f"O_{i}", lowBound=0, cat='Integer') for i in range(months)]
    U = [LpVariable(f"U_{i}", lowBound=0, cat='Integer') for i in range(months)]

    # Objective Function: minimize total cost (hiring, firing, salary, overtime, penalty)
    problem += lpSum(
        H[i] * hiring_cost + F[i] * firing_cost + E[i] * effective_salary_cost +
        O[i] * overtime_cost + U[i] * penalty_cost
        for i in range(months)
    ), "Total_Cost"

    # Constraints
    for i in range(months):
        # Workforce balance: first month uses initial employees, then update each month
        if i == 0:
            problem += E[i] == initial_employees + H[i] - F[i], f"Initial_Balance_{i}"
        else:
            problem += E[i] == E[i-1] + H[i] - F[i], f"Balance_{i}"

        # Production capacity: regular hours + overtime + slack must cover demand (adjusted by service rate)
        problem += E[i] * working_hours + O[i] + U[i] >= demand[i] * service_rate, f"Demand_Cover_{i}"

        # Hiring and firing capacity constraints
        problem += H[i] <= maxh, f"Hiring_Capacity_{i}"
        problem += F[i] <= maxf, f"Firing_Capacity_{i}"

        # Overtime hours constraint: total overtime cannot exceed allowed overtime per employee
        problem += O[i] <= E[i] * overtime_rate, f"Overtime_Limit_{i}"

        # Unmet demand constraint: slack covers any production shortfall
        problem += U[i] >= demand[i] - (E[i] * working_hours + O[i]), f"Unmet_Demand_{i}"

    # Budget constraint: total cost (excluding penalty cost) must not exceed the budget
    total_cost = lpSum(
        H[i] * hiring_cost + F[i] * firing_cost + E[i] * effective_salary_cost +
        O[i] * overtime_cost for i in range(months)
    )
    problem += total_cost <= budget, "Budget_Constraint"

    # Solve the optimization problem using CBC solver with messages enabled
    problem.solve(PULP_CBC_CMD(msg=True))

    # Safe extraction of variable values (defaulting to 0 if not available)
    def safe_value(var):
        return var.value() if var.value() is not None else 0

    # Calculate penalty component (if needed)
    objective_penalty = sum(safe_value(U[i]) * penalty_cost for i in range(months))
    
    results = {
        "Status": LpStatus[problem.status],
        "Total Cost": problem.objective.value() - objective_penalty,
        "Details": []
    }

    for i in range(months):
        results["Details"].append({
            "Month": i + 1,
            "Demand (hours)": demand[i],
            "Hired": safe_value(H[i]),
            "Fired": safe_value(F[i]),
            "Employees": safe_value(E[i]),
            "Overtime (hours)": safe_value(O[i]),
            "Unmet Demand (hours)": safe_value(U[i])
        })

    return results

# ----------------- Streamlit App -----------------
st.title("Workforce Planning Optimization Model")

# Sidebar: Dynamic Grade Inputs
st.sidebar.header("Grade Settings")
num_grades = st.sidebar.number_input("Number of Grades", min_value=1, value=1, step=1)
grade_data = []  # List to store tuples: (grade_name, count, salary)
for i in range(int(num_grades)):
    # Create three columns for a nicer layout
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        grade_name = st.text_input(f"Grade {i+1} Name", value=f"Grade {i+1}", key=f"grade_name_{i}")
    with col2:
        count = st.number_input(f"Count for {grade_name}", min_value=0, value=0, key=f"grade_count_{i}")
    with col3:
        salary = st.number_input(f"Salary for {grade_name}", min_value=0, value=0, key=f"grade_salary_{i}")
    grade_data.append((grade_name, count, salary))

# Compute total initial employees and effective salary cost
if grade_data:
    total_initial = sum(count for (_, count, _) in grade_data)
    if total_initial > 0:
        effective_salary_cost = sum(count * salary for (_, count, salary) in grade_data) / total_initial
    else:
        effective_salary_cost = 0
else:
    total_initial = 0
    effective_salary_cost = 0

st.sidebar.markdown(f"**Total Initial Employees (from grades):** {total_initial}")
st.sidebar.markdown(f"**Effective Salary Cost:** {effective_salary_cost:,.2f}")

# Other input parameters (using existing code structure)
st.sidebar.header("Other Input Parameters")

months = st.sidebar.number_input("Number of Months", min_value=1, max_value=24, value=12, step=1)

# Cost parameters (hiring, firing, penalty, overtime remain as before)
hiring_cost = st.sidebar.number_input("Hiring Cost", value=1000, step=100)
firing_cost = st.sidebar.number_input("Firing Cost", value=1000, step=100)
penalty_cost = st.sidebar.number_input("Penalty for Unmet Demand", value=100)
overtime_cost = st.sidebar.number_input("Overtime Cost", value=75, step=10)

# Workforce parameters – use the total_initial from grade settings
initial_employees = total_initial  
maxh = st.sidebar.number_input("Maximum Hiring per Month", min_value=1, value=10)
maxf = st.sidebar.number_input("Maximum Firing per Month", min_value=1, value=5)
overtime_rate = st.sidebar.number_input("Overtime Hours per Employee", min_value=1, value=10)
working_hours = st.sidebar.number_input("Working Hours per Employee per Month", min_value=1, value=166)

# Budget and service rate
use_auto_budget = st.sidebar.checkbox("Auto-calculate Budget", value=True)

if use_auto_budget:
    budget = total_initial * effective_salary_cost * months
    st.sidebar.markdown(f"**Auto-Calculated Budget:** {budget:,.0f}")
else:
    budget = st.sidebar.number_input("Manual Budget", min_value=0, value=10000000, step=10000)
st.sidebar.markdown(f"**Budget:** {budget:,.0f}")
service_rate = st.sidebar.slider("Service Rate", min_value=0.0, max_value=1.0, value=0.95)

# Demand input for each month (in hours)
st.sidebar.header("Monthly Demand (hours)")
demand = []
for i in range(int(months)):
    default_demand = initial_employees * 166  # For example, a base calculation
    d = st.sidebar.number_input(f"Demand for Month {i+1}", min_value=0, value=default_demand, step=100, key=f"demand_{i}")
    demand.append(d)

# ----------------- Solve and Display Results -----------------
if st.button("Optimize"):
    with st.spinner("Solving the optimization model..."):
        results = solve_workforce_planning(
            int(months), hiring_cost, firing_cost, effective_salary_cost, penalty_cost,
            overtime_cost, initial_employees, maxh, maxf, overtime_rate,
            working_hours, demand, budget, service_rate
        )

    st.subheader("Optimization Results")
    if results['Status'] == 'Optimal':
        st.success(f"Status: {results['Status']}")
        st.write(f"Total Cost: {results['Total Cost']:,}")

        # Calculate variance (budget minus total cost)
        total_cost_value = results['Total Cost']
        variance = budget - total_cost_value
        percentage_variance = (variance / budget * 100) if budget > 0 else 0

        # Choose card color and icon based on variance
        if variance >= 0:
            card_color = "#28a745"  # Green for under budget
            icon = "✅"
            variance_text = "Under Budget"
        else:
            card_color = "#dc3545"  # Red for over budget
            icon = "⚠️"
            variance_text = "Over Budget"

        st.markdown(f"""
        <div style="background-color: {card_color}; padding: 15px; border-radius: 5px; color: white; text-align: center;">
            <h2>{icon} {variance_text}</h2>
            <p style="font-size: 20px;">Variance: {variance:,.0f} units</p>
            <p style="font-size: 16px;">({percentage_variance:.2f}%)</p>
        </div>
        """, unsafe_allow_html=True)

        # Display results in a table
        df = pd.DataFrame(results["Details"])
        st.write("Results in a Tabular Form:")
        st.dataframe(df)
   
        # Plot: Hired vs Fired per Month
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=df['Month'], y=df['Hired'], name='Hired', marker_color='green'))
        fig1.add_trace(go.Bar(x=df['Month'], y=df['Fired'], name='Fired', marker_color='red'))
        fig1.update_layout(barmode='group', xaxis_title='Month', yaxis_title='Count',
                           title='Hired vs Fired Employees per Month')
        st.plotly_chart(fig1)
   
        # Plot: Overtime vs Unmet Demand
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df['Month'], y=df['Overtime (hours)'], name='Overtime', marker_color='blue'))
        fig2.add_trace(go.Bar(x=df['Month'], y=df['Unmet Demand (hours)'], name='Unmet Demand', marker_color='orange'))
        fig2.update_layout(barmode='group', xaxis_title='Month', yaxis_title='Hours',
                           title='Overtime vs Unmet Demand per Month')
        st.plotly_chart(fig2)
   
        # Plot: Total Workforce Capacity vs Demand
        df['Total Workforce Capacity'] = df['Employees'] * working_hours + df['Overtime (hours)']
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df['Month'], y=df['Total Workforce Capacity'], mode='lines+markers',
                                  name='Total Workforce Capacity', line=dict(color='green')))
        fig3.add_trace(go.Scatter(x=df['Month'], y=df['Demand (hours)'], mode='lines+markers',
                                  name='Demand', line=dict(color='red')))
        fig3.update_layout(xaxis_title='Month', yaxis_title='Hours',
                           title='Total Workforce Capacity vs Demand',
                           xaxis=dict(tickmode='linear', dtick=1))
        st.plotly_chart(fig3)
   
        # Cost Distribution Pie Chart
        hiring_total_cost = sum(df['Hired']) * hiring_cost
        firing_total_cost = sum(df['Fired']) * firing_cost
        salary_total_cost = sum(df['Employees']) * effective_salary_cost
        overtime_total_cost = sum(df['Overtime (hours)']) * overtime_cost
        penalty_total_cost = sum(df['Unmet Demand (hours)']) * penalty_cost
       
        costs = [hiring_total_cost, firing_total_cost, salary_total_cost,
                 overtime_total_cost, penalty_total_cost]
        labels = ['Hiring Cost', 'Firing Cost', 'Salary Cost', 'Overtime Cost', 'Penalty Cost']
       
        fig4 = go.Figure(data=[go.Pie(labels=labels, values=costs, textinfo='percent+label')])
        fig4.update_layout(title='Cost Distribution')
        st.plotly_chart(fig4)
   
    else:
        st.error(f"Status: {results['Status']}")
