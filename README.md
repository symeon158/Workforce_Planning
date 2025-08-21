# Workforce Planning Optimization Model

This repository contains a dynamic, interactive workforce planning optimization model built with **Python**, **Streamlit**, and **PuLP**.  
The application helps organizations make informed workforce decisions by optimizing hiring, firing, and overtime usage while minimizing overall costs.

👉 **[Launch Workforce Planning App](https://workforceplanning-mdrxrdzzkx9uyo5k8zvfuk.streamlit.app/)**  

---

## Features

- **Dynamic Grade Management**  
  Input and manage multiple employee grades (e.g., Grade 1, Grade 2, etc.) with customizable counts and salary costs.  
  The app calculates an effective (weighted average) salary cost based on your grade distribution for more realistic planning.

- **Comprehensive Cost Optimization**  
  The optimization model minimizes the total cost comprising:
  - Hiring
  - Firing
  - Salary
  - Overtime
  - Penalties for unmet demand  
  All while ensuring workforce balance, respecting overtime limits, and staying within a predefined budget.

- **User-Friendly Interface**  
  Built with Streamlit, the app offers an intuitive sidebar for configuring:
  - Model parameters (number of months, workforce parameters, cost factors)
  - Demand (in hours)
  - Grade distribution  
  This makes it easy to adjust the model dynamically based on your needs.

- **Interactive Visualizations**  
  Results are displayed in an interactive dashboard using Plotly, including:
  - Tabular results per period
  - Bar charts for hired vs. fired employees
  - Comparisons of overtime vs. unmet demand
  - A line chart comparing total workforce capacity with demand
  - A cost distribution pie chart
  - A dynamic variance card showing the difference between the total cost and the budget (absolute and percentage), with styling to indicate whether the project is under or over budget.

---

## Mathematical Formulation

The core of this project is a **Linear Programming (LP)** model that minimizes the total cost of workforce management over a planning horizon (measured in months).  
The model considers various cost components (hiring, firing, salary, overtime, and penalties for unmet demand) while ensuring that production capacity meets demand and total cost remains within budget.

### Decision Variables

For each month \( i \) (\( i = 1, 2, \dots, N \), with \( N \) being the number of months):

- \( H_i \): Number of employees hired in month \( i \).
- \( F_i \): Number of employees fired in month \( i \).
- \( E_i \): Total number of employees at the end of month \( i \).
- \( O_i \): Total overtime hours worked in month \( i \).
- \( U_i \): Unmet demand (in hours) in month \( i \) that incurs a penalty.

### Objective Function

The goal is to **minimize the total cost**:

\[
Z = \sum_{i=1}^{N} \Big( 
\text{hiring\_cost} \cdot H_i +
\text{firing\_cost} \cdot F_i +
\text{salary\_cost} \cdot E_i +
\text{overtime\_cost} \cdot O_i +
\text{penalty\_cost} \cdot U_i
\Big)
\]

### Constraints

1. **Workforce Balance**
   - First month:  
     \[
     E_1 = \text{initial\_employees} + H_1 - F_1
     \]
   - Subsequent months (\( i \geq 2 \)):  
     \[
     E_i = E_{i-1} + H_i - F_i
     \]

2. **Production Capacity**
   \[
   E_i \times \text{working\_hours} + O_i + U_i \geq \text{demand}_i \times \text{service\_rate}
   \]

3. **Overtime Limit**
   \[
   O_i \leq E_i \times \text{overtime\_rate}
   \]

4. **Budget Constraint**
   \[
   \sum_{i=1}^{N} 
   \Big( \text{hiring\_cost} \cdot H_i +
         \text{firing\_cost} \cdot F_i +
         \text{salary\_cost} \cdot E_i +
         \text{overtime\_cost} \cdot O_i
   \Big) \leq \text{Budget}
   \]

---

## Handling Employee Grades

If employees are divided into grades (different salary costs), two approaches can be used:

1. **Effective Salary Cost (Weighted Average)**  
   Example with 750 employees:
   - 500 employees × $1500  
   - 100 employees × $1700  
   - 75 employees × $2000  
   - 75 employees × $2500  

   \[
   \text{Effective Salary Cost} = 
   \frac{(500 \times 1500) + (100 \times 1700) + (75 \times 2000) + (75 \times 2500)}{750}
   \]

2. **Separate Grade Modeling**  
   Introduce variables per grade (\( E_{i,1}, E_{i,2}, \dots \)) with their respective salary costs.  
   This provides more granularity but increases model complexity.

---

## Getting Started

### Prerequisites
- Python 3.x
- [Streamlit](https://streamlit.io/)
- [PuLP](https://coin-or.github.io/pulp/)
- [Plotly](https://plotly.com/python/)
- [Pandas](https://pandas.pydata.org/)

### Installation

```bash
git clone https://github.com/your-username/workforce-planning-optimization.git
cd workforce-planning-optimization
