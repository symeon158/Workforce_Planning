# Workforce Planning Optimization Model

An interactive workforce planning optimizer built with **Python**, **Streamlit**, **PuLP** and **Plotly**.
It decides how many people to hire or let go each month, and how much overtime to use, so that demand is met at the lowest total cost — within your service level target and budget.

👉 **[Launch Workforce Planning App](https://workforceplanning-mdrxrdzzkx9uyo5k8zvfuk.streamlit.app/)**

---

## Features

### Workforce & Grades
- Enter employee grades in an editable table (name, headcount, monthly salary) — add or remove rows freely.
- The app computes total headcount and an effective (weighted average) monthly salary.
- Set working hours per employee, the overtime cap per employee, and expected monthly **attrition** (voluntary leavers).

### Demand Planning
- Generate monthly demand from a pattern: **base hours**, **monthly growth %**, **seasonality amplitude** and **peak month**.
- Choose the first month and a horizon of 1–24 months; months are labelled with real dates (e.g. *Oct 2026*).
- Override any individual month in the demand table.

### Costs & Constraints
- Hiring cost per hire, firing cost per exit, overtime cost per hour, penalty per unmet hour.
- Maximum hires and firings per month.
- **Service level target** — optionally enforced every month, or treated as a soft goal (unmet demand is only penalised).
- **Budget** — auto-calculated as current payroll + a buffer %, or entered manually; the cap can be enforced or switched off.

### Results Dashboard
The model re-solves automatically whenever an input changes (results are cached), and shows:

- **KPIs** — planned spend, budget variance, service level achieved, headcount start → end (with total hires / fires), and savings vs. a *no-action* plan (keep today's headcount and cover gaps with overtime).
- **Capacity vs demand** — stacked regular capacity, overtime and unmet hours against the demand line and the service target.
- **Workforce** — headcount over time, with monthly hires, firings and attrition below it.
- **Costs** — monthly cost by component, cumulative spend vs. the budget line, and a total cost breakdown.
- **Plan table** — the full month-by-month plan with service-level bars and **CSV download**.

### Infeasibility Diagnostics
If no plan satisfies all constraints, the app explains why — e.g. *"Budget is too tight: the cost-optimal plan needs about €1.30M vs. a budget of €1.00M"* — or points to the hiring cap, overtime limit or service target as the blocker.

---

## Mathematical Formulation

The core is a **Mixed-Integer Linear Programming (MILP)** model that minimizes the total cost of workforce management over a planning horizon of $N$ months.

### Decision Variables

For each month $i$ ($i = 1, \dots, N$):

| Variable | Meaning | Type |
|---|---|---|
| $H_i$ | Employees hired in month $i$ | Integer, $0 \le H_i \le H_{\max}$ |
| $F_i$ | Employees fired in month $i$ | Integer, $0 \le F_i \le F_{\max}$ |
| $E_i$ | Employees at the end of month $i$ | Integer, $\ge 0$ |
| $O_i$ | Overtime hours in month $i$ | Continuous, $\ge 0$ |
| $U_i$ | Unmet demand (hours) in month $i$ | Continuous, $\ge 0$ |

### Objective Function

$$
\min Z = \sum_{i=1}^{N} \Big(
c_h H_i + c_f F_i + s \, E_i + c_o O_i + c_p U_i
\Big)
$$

where $c_h$ = hiring cost, $c_f$ = firing cost, $s$ = effective monthly salary, $c_o$ = overtime cost per hour, $c_p$ = penalty per unmet hour.

### Constraints

**1. Workforce balance** (with $E_0$ = initial employees and $a$ = attrition per month)

$$
E_i = E_{i-1} + H_i - F_i - a
$$

**2. Demand coverage** — regular hours plus overtime plus unmet hours cover demand $D_i$

$$
E_i \cdot \mathrm{working\_hours} + O_i + U_i \geq D_i
$$

**3. Overtime limit**

$$
O_i \leq E_i \cdot \mathrm{overtime\_per\_employee}
$$

**4. Service level** (when enforced) — at most $(1 - \sigma)$ of each month's demand may go unmet

$$
U_i \leq (1 - \sigma) \cdot D_i
$$

**5. Budget** (when enforced) — planned spend, excluding penalties, stays within budget

$$
\sum_{i=1}^{N} \Big( c_h H_i + c_f F_i + s \, E_i + c_o O_i \Big) \leq \mathrm{Budget}
$$

---

## Handling Employee Grades

**Effective salary cost (weighted average)** — used by the model today. Example with 750 employees:

- 500 × €1,500
- 100 × €1,700
- 75 × €2,000
- 75 × €2,500

$$
s = \frac{(500 \times 1500) + (100 \times 1700) + (75 \times 2000) + (75 \times 2500)}{750}
$$

**Separate grade modeling** — a possible extension: introduce variables per grade ($E_{i,g}, H_{i,g}, \dots$) with their own salaries and hiring limits. This adds granularity at the cost of model size.

---

## Getting Started

### Prerequisites
- Python 3.10+
- Dependencies in [`requirements.txt`](requirements.txt): Streamlit, PuLP, Pandas, Plotly

> **Note on PuLP versions:** the app pins `pulp==2.9.0`, which bundles the CBC solver.
> PuLP 4.x removed `LpStatus` / `PULP_CBC_CMD` and no longer ships a solver; the code includes
> compatibility helpers, so with PuLP 4 it also works if a solver such as HiGHS is installed
> (`pip install highspy`).

### Installation
```bash
git clone https://github.com/symeon158/Workforce_Planning.git
cd Workforce_Planning
pip install -r requirements.txt
```

### Run
```bash
streamlit run Workforce.py
```

The app opens at `http://localhost:8501`. Defaults (3 sample grades, 60 employees, seasonal demand) produce a plan immediately — replace them with your own data in the sidebar.

---

## Project Structure

```
Workforce_Planning/
├── Workforce.py            # Streamlit app: inputs, MILP model, charts
├── requirements.txt        # Pinned dependencies
├── .streamlit/config.toml  # Theme settings
├── .devcontainer/          # Dev container / Codespaces setup
└── README.md
```
