# Workforce Planning Optimization Model

This repository contains a dynamic, interactive workforce planning optimization model built with Python, Streamlit, and PuLP. The application helps organizations make informed workforce decisions by optimizing hiring, firing, and overtime usage while minimizing overall costs.

## Features

- **Dynamic Grade Management:**  
  Input and manage multiple employee grades (e.g., Grade 1, Grade 2, etc.) with customizable counts and salary costs. The app calculates an effective (weighted average) salary cost based on your grade distribution for more realistic planning.

- **Comprehensive Cost Optimization:**  
  The optimization model minimizes the total cost comprising:
  - Hiring
  - Firing
  - Salary
  - Overtime
  - Penalties for unmet demand  
  All while ensuring workforce balance, respecting overtime limits, and staying within a predefined budget.

- **User-Friendly Interface:**  
  Built with Streamlit, the app offers an intuitive sidebar for configuring:
  - Model parameters (number of months, workforce parameters, cost factors)
  - Demand (in hours)
  - Grade distribution  
  This makes it easy to adjust the model dynamically based on your needs.

- **Interactive Visualizations:**  
  Results are displayed in an interactive dashboard using Plotly, including:
  - Tabular results per period
  - Bar charts for hired vs. fired employees
  - Comparisons of overtime vs. unmet demand
  - A line chart comparing total workforce capacity with demand
  - A cost distribution pie chart
  - A dynamic variance card that shows the difference between the total cost and the budget (both in absolute units and percentage), with styling that indicates whether the project is under or over budget.

## Mathematical Formulation

The core of this project is a **Linear Programming (LP)** model that minimizes the total cost of workforce management over a planning horizon (measured in months). The model considers various cost components, including hiring, firing, salary, overtime, and penalties for unmet demand, while ensuring that production capacity meets the demand and the overall cost remains within the allocated budget.

### Decision Variables

For each month \( i \) (where \( i = 1, 2, \dots, N \), with \( N \) being the number of months):

- **\( H_i \)**: Number of employees hired in month \( i \).
- **\( F_i \)**: Number of employees fired in month \( i \).
- **\( E_i \)**: Total number of employees at the end of month \( i \).
- **\( O_i \)**: Total overtime hours worked in month \( i \).
- **\( U_i \)**: Unmet demand (in hours) in month \( i \) that incurs a penalty.

### Objective Function

The goal is to **minimize the total cost** over the planning horizon. The total cost includes:

- **Hiring Cost:** \( \text{hiring\_cost} \times H_i \)
- **Firing Cost:** \( \text{firing\_cost} \times F_i \)
- **Salary Cost:** \( \text{salary\_cost} \times E_i \)  
  (In practice, this may be computed as an *effective salary cost* weighted by the grade distribution.)
- **Overtime Cost:** \( \text{overtime\_cost} \times O_i \)
- **Penalty Cost:** \( \text{penalty\_cost} \times U_i \)

Mathematically, the objective function is defined as:

\[
\text{Minimize} \quad Z = \sum_{i=1}^{N} \Big( \text{hiring\_cost} \cdot H_i + \text{firing\_cost} \cdot F_i + \text{salary\_cost} \cdot E_i + \text{overtime\_cost} \cdot O_i + \text{penalty\_cost} \cdot U_i \Big)
\]

### Constraints

1. **Workforce Balance:**

   - For the first month:
     \[
     E_1 = \text{initial\_employees} + H_1 - F_1
     \]
   - For subsequent months \( i \geq 2 \):
     \[
     E_i = E_{i-1} + H_i - F_i
     \]

2. **Production Capacity:**

   The available work hours must cover the demand (adjusted by a service rate). If each employee works a fixed number of hours (\( \text{working\_hours} \)) per month, then:
   \[
   E_i \times \text{working\_hours} + O_i + U_i \geq \text{demand}_i \times \text{service\_rate}
   \]
   Here, \( U_i \) acts as a slack variable that captures any shortfall in meeting the demand, with an associated penalty.

3. **Overtime Limit:**

   The total overtime in month \( i \) cannot exceed the product of the number of employees and the maximum overtime allowed per employee:
   \[
   O_i \leq E_i \times \text{overtime\_rate}
   \]

4. **Budget Constraint:**

   The overall cost (excluding the penalty for unmet demand) must remain within the specified budget:
   \[
   \sum_{i=1}^{N} \Big( \text{hiring\_cost} \cdot H_i + \text{firing\_cost} \cdot F_i + \text{salary\_cost} \cdot E_i + \text{overtime\_cost} \cdot O_i \Big) \leq \text{Budget}
   \]

### Handling Employee Grades Dynamically

If employees are divided into different grades (each with its own salary cost), the model can be adjusted dynamically via the interface. Two approaches can be used:

1. **Effective Salary Cost:**  
   Compute a weighted average salary based on a fixed grade distribution. For example, if you have:
   - 500 employees at Grade 1 with a salary of \$1500,
   - 100 employees at Grade 2 with a salary of \$1700,
   - 75 employees at Grade 3 with a salary of \$2000,
   - 75 employees at Grade 4 with a salary of \$2500,  
   
   then the effective salary cost is:
   \[
   \text{Effective Salary Cost} = \frac{(500 \times 1500) + (100 \times 1700) + (75 \times 2000) + (75 \times 2500)}{750}
   \]

2. **Separate Grade Modeling:**  
   Introduce separate decision variables for each grade (e.g., \( E_{i,1}, E_{i,2}, \dots \)) and include the respective salary costs in the objective function. This approach provides more granularity but increases the model's complexity.

---

This formulation forms the backbone of the optimization model, ensuring that all aspects of workforce management—from staffing changes to cost controls—are handled in a mathematically rigorous way.


## Getting Started

### Prerequisites

- **Python 3.x**
- [Streamlit](https://streamlit.io/)
- [PuLP](https://coin-or.github.io/pulp/)
- [Plotly](https://plotly.com/python/)
- [Pandas](https://pandas.pydata.org/)

### Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-username/workforce-planning-optimization.git
   cd workforce-planning-optimization
