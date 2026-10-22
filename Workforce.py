import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import pulp
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Workforce Planning",
    page_icon="👷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================== PALETTE (validated categorical order) =====================
C_BLUE = "#2a78d6"      # slot 1
C_ORANGE = "#eb6834"    # slot 2
C_AQUA = "#1baf7a"      # slot 3
C_YELLOW = "#eda100"    # slot 4
C_MAGENTA = "#e87ba4"   # slot 5
C_CRITICAL = "#d03b3b"  # status: unmet demand
C_MUTED = "#898781"     # axes, reference lines (readable on light and dark)
C_GRID = "rgba(137,135,129,0.22)"


# ===================== SOLVER COMPATIBILITY =====================
# PuLP 4.x removed LpStatus / PULP_CBC_CMD and stopped bundling CBC.
# These helpers work on PuLP 2.x (bundled CBC) as well as 4.x (HiGHS etc.).
def _get_solver(time_limit=30):
    for name in ("PULP_CBC_CMD", "HiGHS", "HiGHS_CMD", "COIN_CMD", "GLPK_CMD"):
        try:
            solver = pulp.getSolver(name, msg=False, timeLimit=time_limit)
        except Exception:
            continue
        if solver.available():
            return solver
    raise RuntimeError(
        "No MILP solver available. Install 'pulp<3' (bundled CBC) or 'highspy'."
    )


def _new_var(prob, name, low=0, up=None, cat="Continuous"):
    if hasattr(prob, "add_variable"):  # PuLP 4.x
        return prob.add_variable(name, low, up, cat)
    return pulp.LpVariable(name, low, up, cat=cat)


def _status_name(status):
    status = getattr(status, "status", status)  # PuLP 4.x returns LpSolveStats
    if hasattr(pulp, "LpStatus"):
        return pulp.LpStatus.get(status, str(status))
    try:
        return pulp.LpSolveStatus(status).name
    except Exception:
        return str(status)


# ===================== OPTIMIZER =====================
@st.cache_data(show_spinner=False)
def solve_plan(demand, initial, salary, working_hours, ot_per_emp, max_hire, max_fire,
               attrition, hire_cost, fire_cost, ot_cost, penalty_cost,
               service_level, service_hard, budget, budget_hard):
    """
    Minimise hiring + firing + salary + overtime + unmet-demand penalty.

    E[t] = E[t-1] + H[t] - F[t] - attrition
    E[t]*hours + O[t] + U[t] >= demand[t]      (U = unmet hours, penalised)
    O[t] <= ot_per_emp * E[t]
    U[t] <= (1 - service_level) * demand[t]    (only if service_hard)
    planned spend (excl. penalties) <= budget  (only if budget_hard)
    """
    months = len(demand)
    prob = pulp.LpProblem("Workforce_Planning", pulp.LpMinimize)

    H = [_new_var(prob, f"hire_{t}", 0, max_hire, "Integer") for t in range(months)]
    F = [_new_var(prob, f"fire_{t}", 0, max_fire, "Integer") for t in range(months)]
    E = [_new_var(prob, f"emp_{t}", 0, None, "Integer") for t in range(months)]
    O = [_new_var(prob, f"ot_{t}") for t in range(months)]
    U = [_new_var(prob, f"unmet_{t}") for t in range(months)]

    planned = pulp.lpSum(
        H[t] * hire_cost + F[t] * fire_cost + E[t] * salary + O[t] * ot_cost
        for t in range(months)
    )
    prob += planned + pulp.lpSum(U[t] * penalty_cost for t in range(months)), "Total_Cost"

    for t in range(months):
        prev = initial if t == 0 else E[t - 1]
        prob += E[t] == prev + H[t] - F[t] - attrition, f"Balance_{t}"
        prob += O[t] <= ot_per_emp * E[t], f"Overtime_Limit_{t}"
        prob += E[t] * working_hours + O[t] + U[t] >= demand[t], f"Demand_Cover_{t}"
        if service_hard:
            prob += U[t] <= (1 - service_level) * demand[t], f"Service_Level_{t}"
    if budget_hard:
        prob += planned <= budget, "Budget_Constraint"

    status = _status_name(prob.solve(_get_solver()))
    if status != "Optimal":
        return {"status": status, "plan": None}

    def val(x):
        return round(x.value() or 0, 4)

    plan = [
        {"hires": int(round(val(H[t]))), "fires": int(round(val(F[t]))),
         "employees": int(round(val(E[t]))), "overtime": val(O[t]), "unmet": val(U[t])}
        for t in range(months)
    ]
    return {"status": status, "plan": plan}


def build_results(plan, demand, labels, p):
    df = pd.DataFrame(plan)
    df.insert(0, "Month", labels)
    df.insert(1, "Demand (h)", demand)
    df["Attrition"] = p["attrition"]
    df["Regular capacity (h)"] = df["employees"] * p["working_hours"]
    df["Served (h)"] = (df["Regular capacity (h)"] + df["overtime"]).clip(upper=df["Demand (h)"])
    df["Service level"] = (df["Served (h)"] / df["Demand (h)"].where(df["Demand (h)"] > 0)).fillna(1.0)
    df["Salary cost"] = df["employees"] * p["salary"]
    df["Overtime cost"] = df["overtime"] * p["ot_cost"]
    df["Hiring cost"] = df["hires"] * p["hire_cost"]
    df["Firing cost"] = df["fires"] * p["fire_cost"]
    df["Penalty cost"] = df["unmet"] * p["penalty_cost"]
    df["Planned spend"] = df[["Salary cost", "Overtime cost", "Hiring cost", "Firing cost"]].sum(axis=1)
    df["Cumulative spend"] = df["Planned spend"].cumsum()
    return df.rename(columns={
        "employees": "Employees", "hires": "Hires", "fires": "Fires",
        "overtime": "Overtime (h)", "unmet": "Unmet (h)",
    })


def static_baseline_cost(demand, p):
    """Cost of keeping today's workforce (minus attrition) and covering gaps with overtime."""
    emp, total = p["initial"], 0.0
    for d in demand:
        emp = max(emp - p["attrition"], 0)
        gap = max(d - emp * p["working_hours"], 0)
        ot = min(gap, emp * p["ot_per_emp"])
        total += emp * p["salary"] + ot * p["ot_cost"] + (gap - ot) * p["penalty_cost"]
    return total


def demand_pattern(base, months, growth_pct, season_pct, peak_month, start):
    out = []
    for t in range(months):
        cal_month = (start.month - 1 + t) % 12 + 1
        dist = min(abs(cal_month - peak_month), 12 - abs(cal_month - peak_month))  # 0..6
        season = 1 + season_pct / 100 * (1 - dist / 3)  # +amp at peak, -amp 6 months away
        out.append(int(round(base * (1 + growth_pct / 100) ** t * season, -1)))
    return out


# ===================== CHART HELPERS =====================
def style_fig(fig, height=400, y_title=None, money=False):
    fig.update_layout(
        height=height,
        margin=dict(l=70, r=20, t=50, b=50),
        hovermode="x unified",
        bargap=0.35,
        barcornerradius=4,
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0, title=None,
                    traceorder="normal"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, linecolor=C_GRID, tickfont_color=C_MUTED, automargin=True)
    fig.update_yaxes(gridcolor=C_GRID, automargin=True, zeroline=True, zerolinecolor=C_GRID,
                     tickfont_color=C_MUTED, title_font_color=C_MUTED,
                     title_text=y_title, tickformat="~s" if money else ",")
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


def capacity_chart(df, service_level):
    fig = go.Figure()
    fig.add_bar(x=df["Month"], y=df["Regular capacity (h)"], name="Regular capacity", marker_color=C_BLUE,
                hovertemplate="%{y:,.0f} h")
    fig.add_bar(x=df["Month"], y=df["Overtime (h)"], name="Overtime", marker_color=C_ORANGE,
                hovertemplate="%{y:,.0f} h")
    fig.add_bar(x=df["Month"], y=df["Unmet (h)"], name="Unmet demand", marker_color=C_CRITICAL,
                hovertemplate="%{y:,.0f} h")
    fig.add_scatter(x=df["Month"], y=df["Demand (h)"], name="Demand", mode="lines+markers",
                    line=dict(color=C_MUTED, width=2), marker=dict(size=8),
                    hovertemplate="%{y:,.0f} h")
    fig.add_scatter(x=df["Month"], y=df["Demand (h)"] * service_level,
                    name=f"Service target ({service_level:.0%})", mode="lines",
                    line=dict(color=C_MUTED, width=1.5, dash="dot"), hovertemplate="%{y:,.0f} h")
    fig.update_layout(barmode="stack")
    return style_fig(fig, height=430, y_title="Hours")


def workforce_chart(df, initial):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_heights=[0.6, 0.4], subplot_titles=("Headcount", "Monthly movements"))
    fig.add_scatter(x=df["Month"], y=df["Employees"], name="Employees", mode="lines+markers",
                    line=dict(color=C_BLUE, width=2), marker=dict(size=8), row=1, col=1)
    fig.add_hline(y=initial, line=dict(color=C_MUTED, width=1, dash="dot"),
                  annotation_text=f"Start: {initial}", annotation_font_color=C_MUTED, row=1, col=1)
    fig.add_bar(x=df["Month"], y=df["Hires"], name="Hires", marker_color=C_AQUA, row=2, col=1)
    fig.add_bar(x=df["Month"], y=-df["Fires"], name="Fires", marker_color=C_ORANGE,
                customdata=df["Fires"], hovertemplate="%{customdata}", row=2, col=1)
    if df["Attrition"].sum() > 0:
        fig.add_bar(x=df["Month"], y=-df["Attrition"], name="Attrition", marker_color=C_YELLOW,
                    customdata=df["Attrition"], hovertemplate="%{customdata}", row=2, col=1)
    fig.update_layout(barmode="relative")
    fig.update_annotations(font_color=C_MUTED, font_size=13, selector=dict(text="Headcount"))
    fig.update_annotations(font_color=C_MUTED, font_size=13, selector=dict(text="Monthly movements"))
    return style_fig(fig, height=500, y_title="People")


def monthly_cost_chart(df, cur):
    fig = go.Figure()
    for col, color in [("Salary cost", C_BLUE), ("Overtime cost", C_ORANGE), ("Hiring cost", C_AQUA),
                       ("Firing cost", C_YELLOW), ("Penalty cost", C_MAGENTA)]:
        if df[col].sum() > 0:
            fig.add_bar(x=df["Month"], y=df[col], name=col.replace(" cost", ""), marker_color=color,
                        hovertemplate=f"{cur}%{{y:,.0f}}")
    fig.update_layout(barmode="stack")
    return style_fig(fig, height=400, y_title=f"Cost ({cur})", money=True)


def cumulative_chart(df, budget, cur):
    fig = go.Figure()
    fig.add_scatter(x=df["Month"], y=df["Cumulative spend"], name="Cumulative planned spend",
                    mode="lines+markers", line=dict(color=C_BLUE, width=2), marker=dict(size=8),
                    fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
                    hovertemplate=f"{cur}%{{y:,.0f}}")
    fig.add_hline(y=budget, line=dict(color=C_MUTED, width=1.5, dash="dot"),
                  annotation_text=f"Budget {cur}{budget:,.0f}", annotation_position="top left",
                  annotation_font_color=C_MUTED)
    fig.update_layout(showlegend=False)
    return style_fig(fig, height=360, y_title=f"Cost ({cur})", money=True)


def breakdown_chart(df, cur):
    totals = df[["Salary cost", "Overtime cost", "Hiring cost", "Firing cost", "Penalty cost"]].sum()
    totals = totals[totals > 0].sort_values()
    share = totals / totals.sum()
    fig = go.Figure(go.Bar(
        x=totals.values, y=[i.replace(" cost", "") for i in totals.index], orientation="h",
        marker_color=C_BLUE, text=[f"{cur}{v:,.0f} · {s:.0%}" for v, s in zip(totals, share)],
        textposition="outside", textfont_color=C_MUTED, cliponaxis=False,
        hovertemplate=f"{cur}%{{x:,.0f}}<extra></extra>",
    ))
    fig = style_fig(fig, height=360, money=True)
    fig.update_layout(hovermode="closest", margin=dict(l=90, r=120))
    fig.update_xaxes(showgrid=True, gridcolor=C_GRID)
    fig.update_yaxes(showgrid=False, title_text=None, tickfont_color=None)
    return fig


# ===================== STYLES & HEADER =====================
st.markdown("""
<style>
  .wf-hero {border-left: 4px solid #2a78d6; padding: 0.2rem 0 0.2rem 1rem; margin-bottom: 1.2rem;}
  .wf-hero h1 {font-size: 1.9rem; font-weight: 700; margin: 0; padding: 0;}
  .wf-hero p {margin: 0.25rem 0 0 0; opacity: 0.7; font-size: 0.95rem;}
  div[data-testid="stMetric"] {
    border: 1px solid rgba(137,135,129,0.25); border-radius: 0.75rem; padding: 0.8rem 1rem;
  }
  div[data-testid="stMetricLabel"] p {font-size: 0.8rem; opacity: 0.75;}
</style>
<div class="wf-hero">
  <h1>Workforce Planning Optimizer</h1>
  <p>Mixed-integer optimization of headcount, hiring, overtime and budget against monthly demand.</p>
</div>
""", unsafe_allow_html=True)

# ===================== SIDEBAR INPUTS =====================
DEFAULT_GRADES = pd.DataFrame({
    "Grade": ["Operators", "Technicians", "Supervisors"],
    "Headcount": [40, 15, 5],
    "Monthly salary": [1400.0, 1900.0, 2800.0],
})

with st.sidebar:
    st.header("Inputs")
    cur = st.text_input("Currency symbol", value="€", max_chars=3)

    with st.expander("👥 Workforce & grades", expanded=True):
        grades = st.data_editor(
            DEFAULT_GRADES, key="grades", num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Headcount": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
                "Monthly salary": st.column_config.NumberColumn(min_value=0.0, step=50.0, format="%.0f"),
            },
        )
        grades = grades.dropna(subset=["Headcount", "Monthly salary"])
        initial = int(grades["Headcount"].sum())
        salary = float((grades["Headcount"] * grades["Monthly salary"]).sum() / initial) if initial else 0.0
        c1, c2 = st.columns(2)
        c1.metric("Headcount", f"{initial:,}")
        c2.metric("Avg salary", f"{cur}{salary:,.0f}")
        working_hours = st.number_input("Working hours / employee / month", 1, 400, 166)
        ot_per_emp = st.number_input("Max overtime hours / employee / month", 0, 200, 20)
        attrition = st.number_input("Expected attrition (people / month)", 0, 1000, 0,
                                    help="Voluntary leavers per month, outside of planned firings.")

    with st.expander("📅 Horizon & demand", expanded=True):
        start = st.date_input("First month", value=dt.date.today().replace(day=1))
        months = st.slider("Months", 1, 24, 12)
        base_demand = st.number_input("Base demand (hours / month)", 0, 10_000_000,
                                      int(initial * working_hours), step=100,
                                      help="Defaults to current regular capacity.")
        growth = st.number_input("Growth per month (%)", -20.0, 20.0, 1.0, step=0.5)
        season = st.slider("Seasonality amplitude (%)", 0, 50, 15)
        peak = st.selectbox("Peak month", range(1, 13), index=5,
                            format_func=lambda m: dt.date(2000, m, 1).strftime("%B"))

    with st.expander("💶 Costs", expanded=False):
        hire_cost = st.number_input(f"Hiring cost per hire ({cur})", 0, 1_000_000, 1500, step=100)
        fire_cost = st.number_input(f"Firing cost per exit ({cur})", 0, 1_000_000, 2500, step=100)
        ot_cost = st.number_input(f"Overtime cost per hour ({cur})", 0.0, 10_000.0, 15.0, step=1.0)
        penalty_cost = st.number_input(f"Penalty per unmet hour ({cur})", 0.0, 10_000.0, 40.0, step=5.0,
                                       help="Opportunity cost of demand you fail to serve.")

    with st.expander("⚙️ Constraints", expanded=False):
        max_hire = st.number_input("Max hires / month", 0, 10_000, 10)
        max_fire = st.number_input("Max firings / month", 0, 10_000, 5)
        service_level = st.slider("Service level target (%)", 0, 100, 95) / 100
        service_hard = st.toggle("Enforce service level every month", value=True,
                                 help="Off: unmet demand is only penalised, never forbidden.")
        baseline_payroll = initial * salary * months
        auto_budget = st.toggle("Auto budget (payroll + buffer)", value=True)
        if auto_budget:
            buffer_pct = st.slider("Budget buffer over current payroll (%)", 0, 100, 15)
            budget = baseline_payroll * (1 + buffer_pct / 100)
            st.caption(f"Budget: **{cur}{budget:,.0f}**")
        else:
            budget = float(st.number_input(f"Budget ({cur})", 0, 10**10, int(baseline_payroll * 1.15),
                                           step=10_000))
        budget_hard = st.toggle("Enforce budget cap", value=True)

# ===================== DEMAND TABLE =====================
labels = [d.strftime("%b %Y") for d in pd.date_range(start, periods=months, freq="MS")]
pattern = demand_pattern(base_demand, months, growth, season, peak, start)
sig = hash((tuple(pattern), tuple(labels)))  # new pattern -> fresh editor

with st.expander("📈 Monthly demand — edit any month to override the pattern", expanded=False):
    demand_df = st.data_editor(
        pd.DataFrame({"Month": labels, "Demand (h)": pattern}),
        key=f"demand_{sig}", hide_index=True, width="stretch", disabled=["Month"],
        column_config={"Demand (h)": st.column_config.NumberColumn(min_value=0, step=100, format="%d")},
    )
demand = [int(x) if pd.notna(x) else 0 for x in demand_df["Demand (h)"]]

# ===================== SOLVE =====================
if initial == 0 and sum(demand) > 0 and max_hire == 0:
    st.warning("No employees and hiring is disabled — every hour of demand will go unmet.")
if salary == 0:
    st.info("Average salary is 0 — enter salaries in **Workforce & grades** for meaningful costs.")

p = dict(initial=initial, salary=salary, working_hours=int(working_hours), ot_per_emp=int(ot_per_emp),
         max_hire=int(max_hire), max_fire=int(max_fire), attrition=int(attrition),
         hire_cost=float(hire_cost), fire_cost=float(fire_cost), ot_cost=float(ot_cost),
         penalty_cost=float(penalty_cost), service_level=float(service_level),
         service_hard=bool(service_hard), budget=float(budget), budget_hard=bool(budget_hard))

with st.spinner("Optimizing…"):
    try:
        result = solve_plan(tuple(demand), **p)
    except Exception as exc:
        st.error(f"Solver error: {exc}")
        st.stop()

if result["plan"] is None:
    st.error(f"No feasible plan (solver status: **{result['status']}**).")
    hints = []
    if budget_hard:
        relaxed = solve_plan(tuple(demand), **{**p, "budget_hard": False})
        if relaxed["plan"] is not None:
            need = build_results(relaxed["plan"], demand, labels, p)["Planned spend"].sum()
            hints.append(f"**Budget is too tight.** The cost-optimal plan needs about "
                         f"{cur}{need:,.0f} vs. a budget of {cur}{budget:,.0f}. "
                         "Raise the budget/buffer or turn off *Enforce budget cap*.")
    if service_hard and not hints:
        hints.append(f"**The {service_level:.0%} service level can't be reached** with the current "
                     "hiring cap, overtime limit and attrition. Raise *Max hires / month* or overtime "
                     "hours, lower the target, or turn off *Enforce service level every month*.")
    if attrition and not hints:
        hints.append("Attrition may exceed headcount plus allowed hires — lower attrition or raise hiring.")
    for h in hints:
        st.markdown(f"- {h}")
    st.stop()

df = build_results(result["plan"], demand, labels, p)

# ===================== KPIs =====================
planned_total = df["Planned spend"].sum()
penalty_total = df["Penalty cost"].sum()
variance = budget - planned_total
overall_service = df["Served (h)"].sum() / max(df["Demand (h)"].sum(), 1)
savings = static_baseline_cost(demand, p) - (planned_total + penalty_total)

k = st.columns(5)
k[0].metric("Planned spend", f"{cur}{planned_total:,.0f}",
            help="Salaries + overtime + hiring + firing (excludes penalties).")
k[1].metric("Budget variance", f"{cur}{abs(variance):,.0f}",
            delta=f"{'under' if variance >= 0 else 'over'} budget ({variance / budget:+.1%})" if budget else None,
            delta_color="normal" if variance >= 0 else "inverse")
k[2].metric("Service level achieved", f"{overall_service:.1%}",
            delta=f"{overall_service - service_level:+.1%} vs target",
            delta_color="normal" if overall_service >= service_level else "inverse")
k[3].metric("Headcount (start → end)", f"{initial} → {int(df['Employees'].iloc[-1])}",
            delta=f"{int(df['Hires'].sum())} hires · {int(df['Fires'].sum())} fires", delta_color="off")
k[4].metric("Savings vs. no-action plan", f"{cur}{savings:,.0f}",
            help="Compared with keeping today's headcount and covering gaps with overtime, "
                 "paying the penalty for the rest.", delta_color="off")

if penalty_total > 0:
    st.caption(f"⚠️ {df['Unmet (h)'].sum():,.0f} hours of demand remain unmet "
               f"(penalty {cur}{penalty_total:,.0f}, not counted in planned spend).")

# ===================== TABS =====================
t_cap, t_wf, t_cost, t_tbl = st.tabs(["Capacity vs demand", "Workforce", "Costs", "Plan table"])

with t_cap:
    show(capacity_chart(df, service_level))

with t_wf:
    show(workforce_chart(df, initial))

with t_cost:
    show(monthly_cost_chart(df, cur))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Cumulative spend vs budget**")
        show(cumulative_chart(df, budget, cur))
    with c2:
        st.markdown("**Total cost breakdown**")
        show(breakdown_chart(df, cur))

with t_tbl:
    money_cols = ["Salary cost", "Overtime cost", "Hiring cost", "Firing cost", "Penalty cost",
                  "Planned spend", "Cumulative spend"]
    cols = ["Month", "Demand (h)", "Employees", "Hires", "Fires", "Attrition", "Regular capacity (h)",
            "Overtime (h)", "Unmet (h)", "Service level"] + money_cols
    st.dataframe(
        df[cols], hide_index=True, width="stretch",
        column_config={
            **{c: st.column_config.NumberColumn(format="%,.0f") for c in
               ["Demand (h)", "Regular capacity (h)", "Overtime (h)", "Unmet (h)"]},
            **{c: st.column_config.NumberColumn(format=f"{cur}%,.0f") for c in money_cols},
            "Service level": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        },
    )
    st.download_button("⬇️ Download plan (CSV)", df[cols].to_csv(index=False).encode("utf-8"),
                       file_name="workforce_plan.csv", mime="text/csv")
