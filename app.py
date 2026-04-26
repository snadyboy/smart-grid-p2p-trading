import streamlit as st

st.set_page_config(
    page_title="⚡ Decentralized Smart Grid",
    page_icon="⚡",
    layout="wide"
)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from core.grid import Grid, GridState
from core.load import Hospital, Commercial, School, Home1, Home2, Home3
from core.renewable import SolarPV
from core.controller import CentralController
from utils.logger import SimulationLogger
from utils.constants import LoadType

logger = SimulationLogger("Dashboard")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_demand_profile(
    start_h: int,
    end_h: int,
    demand_kw: float,
    off_fraction: float = 0.10,
) -> list:
    """
    Build a 24-hour absolute demand profile (kW per hour) from a time block.

    Hours inside [start_h, end_h] receive *demand_kw*.
    Hours outside receive *demand_kw * off_fraction* as a baseline.
    Handles wrap-around midnight (e.g. start_h=22, end_h=4).

    Args:
        start_h: First active hour (0–23, inclusive).
        end_h: Last active hour (0–23, inclusive).
        demand_kw: Power demand during active hours (kW).
        off_fraction: Fraction of demand_kw used as the baseline demand
            during inactive hours (default 10 %).
    """
    baseline = demand_kw * off_fraction
    profile = [baseline] * 24

    if start_h <= end_h:
        active_hours = range(start_h, end_h + 1)
    else:  # wraps midnight
        active_hours = list(range(start_h, 24)) + list(range(0, end_h + 1))

    for h in active_hours:
        profile[h] = demand_kw

    return profile


# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────

st.title("⚡ Smart Grid Power Management")
st.markdown("**Manage electricity for 24 hours**")

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar – infrastructure controls
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ SETTINGS")

grid_capacity  = st.sidebar.slider("⚡ Power Plant Size (kW)", 1000, 5000, 2000, 500)
solar_capacity = st.sidebar.slider("☀️ Solar Panels (kW)",    0,    1000,  500, 100)
battery_capacity = st.sidebar.slider("🔋 Battery Size (kWh)", 50,   500,   200,  50)
base_price     = st.sidebar.slider("💰 Base Price (RS/MWh)",  50,   200,   100,  10)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar – per-component demand blocks
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Component Demand Blocks")
st.sidebar.caption("Set the active hours, demand, and priority for each component. Priority 1 = highest.")

# (label, key, min_kw, max_kw, default_kw, def_start, def_end, def_priority)
_COMP_DEFS = [
    ("🏥 Hospital",   "hospital",   50,  500,  300,  0, 23, 1),
    ("🏢 Commercial", "commercial", 100, 1000, 600,  7, 20, 2),
    ("🏫 School",     "school",     50,  400,  200,  7, 17, 3),
    ("🏠 Home 1",     "home1",      50,  800,  500, 17, 23, 4),
    ("🏠 Home 2",     "home2",      50,  800,  450, 18, 23, 5),
    ("🏠 Home 3",     "home3",      50,  800,  400, 19, 23, 6),
]

comp_settings: dict = {}
for label, key, min_kw, max_kw, default_kw, def_start, def_end, def_prio in _COMP_DEFS:
    with st.sidebar.expander(label, expanded=False):
        c1, c2 = st.columns(2)
        start_h  = c1.number_input("Start Hour", 0, 23, def_start, key=f"{key}_start")
        end_h    = c2.number_input("End Hour",   0, 23, def_end,   key=f"{key}_end")
        demand   = st.slider("Demand (kW)", min_kw, max_kw, default_kw, key=f"{key}_demand")
        priority = st.selectbox(
            "Priority (1 = highest)",
            options=[1, 2, 3, 4, 5, 6],
            index=def_prio - 1,
            key=f"{key}_priority",
        )
    comp_settings[key] = {
        "start_h":   int(start_h),
        "end_h":     int(end_h),
        "demand_kw": int(demand),
        "priority":  int(priority),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Simulation
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(comp_cfg: dict) -> tuple:
    """Run 24-hour grid simulation and return (DataFrame, loads dict, grid)."""
    np.random.seed(42)  # deterministic

    grid       = Grid(main_generation_kw=grid_capacity, battery_capacity_kwh=battery_capacity)
    solar      = SolarPV(capacity_kw=solar_capacity)
    controller = CentralController()

    # Build load objects with custom demand profiles and user-set priorities
    hospital   = Hospital(demand_kw=comp_cfg["hospital"]["demand_kw"])
    commercial = Commercial(demand_kw=comp_cfg["commercial"]["demand_kw"])
    school     = School(demand_kw=comp_cfg["school"]["demand_kw"])
    home1_load = Home1(demand_kw=comp_cfg["home1"]["demand_kw"])
    home2_load = Home2(demand_kw=comp_cfg["home2"]["demand_kw"])
    home3_load = Home3(demand_kw=comp_cfg["home3"]["demand_kw"])

    load_objects = {
        LoadType.HOSPITAL:   hospital,
        LoadType.COMMERCIAL: commercial,
        LoadType.SCHOOL:     school,
        LoadType.HOME1:      home1_load,
        LoadType.HOME2:      home2_load,
        LoadType.HOME3:      home3_load,
    }
    key_map = {
        "hospital":   LoadType.HOSPITAL,
        "commercial": LoadType.COMMERCIAL,
        "school":     LoadType.SCHOOL,
        "home1":      LoadType.HOME1,
        "home2":      LoadType.HOME2,
        "home3":      LoadType.HOME3,
    }

    for cfg_key, lt in key_map.items():
        cfg = comp_cfg[cfg_key]
        profile = build_demand_profile(cfg["start_h"], cfg["end_h"], cfg["demand_kw"])
        load_objects[lt].set_custom_profile(profile)
        load_objects[lt].priority = cfg["priority"]

    history = []

    for hour in range(24):
        # Step 1: calculate demands
        for load in load_objects.values():
            load.calculate_demand(hour, stochastic=True)

        # Step 2: generation
        solar_gen = solar.calculate_generation(hour, stochastic=True)
        main_gen  = grid.main_generation_kw * 0.85
        total_gen_base = main_gen + solar_gen

        # Step 3: totals and SDR
        total_demand = sum(l.current_demand_kw for l in load_objects.values())
        sdr = grid.calculate_sdr(total_gen_base, total_demand)

        # Step 4: battery
        battery_discharge, soc = grid.manage_battery(total_gen_base, total_demand)
        total_gen = total_gen_base + battery_discharge

        # Step 5: allocate
        allocation = controller.allocate_energy_priority_based(total_gen, load_objects)

        # Step 6: optional load shedding
        if sdr < 0.85:
            controller.perform_load_shedding(load_objects, sdr)

        # Step 7: apply allocation and calculate costs
        total_allocated = 0.0
        for lt, load in load_objects.items():
            load.allocate_power(allocation[lt])
            total_allocated += load.allocated_kw

        # Step 8: price
        price = controller.calculate_sdr_based_price(sdr, base_price)

        for load in load_objects.values():
            load.update_cost(price)

        # Step 9: record
        row = {
            "hour":          hour,
            "generation":    total_gen,
            "solar":         solar_gen,
            "demand":        total_demand,
            "allocated":     total_allocated,
            "sdr":           sdr,
            "price":         price,
            "battery_soc":   soc,
        }
        for cfg_key, lt in key_map.items():
            load = load_objects[lt]
            row[f"{cfg_key}_demand"]    = load.current_demand_kw
            row[f"{cfg_key}_allocated"] = load.allocated_kw
            row[f"{cfg_key}_price"]     = price
            row[f"{cfg_key}_cost"]      = load.hourly_cost

        history.append(row)

    return pd.DataFrame(history), load_objects, grid


# Run button
if st.sidebar.button("▶️ START SIMULATION", key="run_sim"):
    with st.spinner("⏳ Running 24-hour simulation..."):
        df_history, loads, grid = run_simulation(comp_settings)
        st.session_state.df_history   = df_history
        st.session_state.loads        = loads
        st.session_state.comp_settings = comp_settings

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard (only shown after simulation has run)
# ─────────────────────────────────────────────────────────────────────────────

if "df_history" in st.session_state:
    df = st.session_state.df_history

    tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "📈 GRAPHS", "📄 DATA", "ℹ️ HELP"])

    # ── Tab 1: Dashboard ──────────────────────────────────────────────────────
    with tab1:
        st.subheader("⚡ POWER STATUS")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Peak Demand",  f"{df['demand'].max():.0f} kW")
        with col2:
            st.metric("Avg SDR",      f"{df['sdr'].mean():.2f}")
        with col3:
            st.metric("Avg Price",    f"RS {df['price'].mean():.2f}/MWh")
        with col4:
            st.metric("Battery Left", f"{df['battery_soc'].iloc[-1]*100:.1f}%")

        st.subheader("⚡ Generation vs Demand (24 h)")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=df["hour"], y=df["generation"], name="⚡ Generation",
            mode="lines+markers", line=dict(color="green", width=3)))
        fig1.add_trace(go.Scatter(
            x=df["hour"], y=df["demand"], name="📊 Total Demand",
            mode="lines+markers", line=dict(color="red", width=3)))
        fig1.update_layout(
            xaxis_title="Hour", yaxis_title="Power (kW)",
            height=400, template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💰 Price Over Time (RS/MWh)")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["hour"], y=df["price"], name="Price",
                mode="lines+markers", line=dict(color="purple", width=3),
                fill="tozeroy"))
            fig2.update_layout(
                xaxis_title="Hour", yaxis_title="RS/MWh",
                height=350, template="plotly_dark")
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.subheader("📊 Supply-Demand Ratio")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=df["hour"], y=df["sdr"], name="SDR",
                mode="lines+markers", line=dict(color="orange", width=3),
                fill="tozeroy"))
            fig3.add_hline(y=1.0, line_dash="dash", line_color="white")
            fig3.update_layout(
                xaxis_title="Hour", yaxis_title="Ratio",
                height=350, template="plotly_dark")
            st.plotly_chart(fig3, use_container_width=True)

        st.subheader("💸 Hourly Cost per Component (RS)")
        fig_cost = go.Figure()
        cost_colors = {
            "hospital":   "red",
            "commercial": "blue",
            "school":     "green",
            "home1":      "orange",
            "home2":      "yellow",
            "home3":      "cyan",
        }
        cost_labels = {
            "hospital":   "🏥 Hospital",
            "commercial": "🏢 Commercial",
            "school":     "🏫 School",
            "home1":      "🏠 Home 1",
            "home2":      "🏠 Home 2",
            "home3":      "🏠 Home 3",
        }
        for key, label in cost_labels.items():
            fig_cost.add_trace(go.Bar(
                x=df["hour"], y=df[f"{key}_cost"],
                name=label, marker_color=cost_colors[key]))
        fig_cost.update_layout(
            barmode="stack", xaxis_title="Hour", yaxis_title="RS",
            height=350, template="plotly_dark")
        st.plotly_chart(fig_cost, use_container_width=True)

    # ── Tab 2: Graphs ─────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Load Demand vs Allocation")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Power Needed (kW)")
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(x=df["hour"], y=df["hospital_demand"],   name="🏥 Hospital",   mode="lines", stackgroup="one"))
            fig5.add_trace(go.Scatter(x=df["hour"], y=df["commercial_demand"], name="🏢 Commercial",  mode="lines", stackgroup="one"))
            fig5.add_trace(go.Scatter(x=df["hour"], y=df["school_demand"],     name="🏫 School",     mode="lines", stackgroup="one"))
            fig5.add_trace(go.Scatter(x=df["hour"], y=df["home1_demand"],      name="🏠 Home 1",     mode="lines", stackgroup="one"))
            fig5.add_trace(go.Scatter(x=df["hour"], y=df["home2_demand"],      name="🏠 Home 2",     mode="lines", stackgroup="one"))
            fig5.add_trace(go.Scatter(x=df["hour"], y=df["home3_demand"],      name="🏠 Home 3",     mode="lines", stackgroup="one"))
            fig5.update_layout(xaxis_title="Hour", yaxis_title="kW", height=400, template="plotly_dark")
            st.plotly_chart(fig5, use_container_width=True)

        with col2:
            st.subheader("Power Allocated (kW)")
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=df["hour"], y=df["hospital_allocated"],   name="🏥 Hospital",   mode="lines", stackgroup="one"))
            fig6.add_trace(go.Scatter(x=df["hour"], y=df["commercial_allocated"], name="🏢 Commercial",  mode="lines", stackgroup="one"))
            fig6.add_trace(go.Scatter(x=df["hour"], y=df["school_allocated"],     name="🏫 School",     mode="lines", stackgroup="one"))
            fig6.add_trace(go.Scatter(x=df["hour"], y=df["home1_allocated"],      name="🏠 Home 1",     mode="lines", stackgroup="one"))
            fig6.add_trace(go.Scatter(x=df["hour"], y=df["home2_allocated"],      name="🏠 Home 2",     mode="lines", stackgroup="one"))
            fig6.add_trace(go.Scatter(x=df["hour"], y=df["home3_allocated"],      name="🏠 Home 3",     mode="lines", stackgroup="one"))
            fig6.update_layout(xaxis_title="Hour", yaxis_title="kW", height=400, template="plotly_dark")
            st.plotly_chart(fig6, use_container_width=True)

        st.subheader("Per-Component Price (RS/MWh) – reflects global SDR price")
        fig_price = go.Figure()
        for key, label in cost_labels.items():
            fig_price.add_trace(go.Scatter(
                x=df["hour"], y=df[f"{key}_price"],
                name=label, mode="lines"))
        fig_price.update_layout(
            xaxis_title="Hour", yaxis_title="RS/MWh",
            height=350, template="plotly_dark")
        st.plotly_chart(fig_price, use_container_width=True)

    # ── Tab 3: Data ───────────────────────────────────────────────────────────
    with tab3:
        st.subheader("📥 Download Simulation Data")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="smart-grid-simulation.csv",
            mime="text/csv",
        )
        st.dataframe(df.round(2), use_container_width=True)

    # ── Tab 4: Help ───────────────────────────────────────────────────────────
    with tab4:
        st.markdown("""
## INSTRUCTIONS

**GOAL:** Keep everyone's lights on for 24 hours!

### Infrastructure sliders (top of sidebar):
| Slider | Description |
|--------|-------------|
| Power Plant Size | Total main-grid capacity (kW) |
| Solar Panels | Peak solar capacity (kW) |
| Battery Size | Energy storage capacity (kWh) |
| Base Price | Starting electricity price (RS/MWh) |

### Component Demand Blocks (expandable sections):
For each component you can set:
- **Start Hour / End Hour** – the active window (0–23). Outside this window the load uses 10% of its demand as a baseline.
- **Demand (kW)** – the power this component draws during its active hours.
- **Priority (1 = highest)** – determines allocation order when generation is scarce.

> If the same component has overlapping hour ranges across multiple runs, the latest block overwrites only the overlapping hours while preserving the rest.

### Default priority order:
1. 🏥 Hospital – critical, must have power
2. 🏢 Commercial – business hours
3. 🏫 School – school hours
4. 🏠 Home 1
5. 🏠 Home 2
6. 🏠 Home 3

### How pricing works:
| Supply-Demand Ratio (SDR) | Price |
|---------------------------|-------|
| SDR > 1.5 (surplus)       | 50% off base price |
| 0.9 ≤ SDR ≤ 1.5 (normal)  | Base price |
| 0.5 ≤ SDR < 0.9 (shortage)| 2× base price |
| SDR < 0.5 (critical)      | 3× base price |

### Output columns per component:
`{name}_demand`, `{name}_allocated`, `{name}_price`, `{name}_cost`
        """)

else:
    st.info("""
👉 Use the sidebar to configure your grid, then click **▶️ START SIMULATION**.

```
Main Grid + Solar PV
        │
        ▼
     Battery
        │
        ▼
   Controller  ← SDR-based pricing & priority allocation
        │
        ├── 🏥 Hospital   (Priority 1)
        ├── 🏢 Commercial (Priority 2)
        ├── 🏫 School     (Priority 3)
        ├── 🏠 Home 1     (Priority 4)
        ├── 🏠 Home 2     (Priority 5)
        └── 🏠 Home 3     (Priority 6)
```
""")