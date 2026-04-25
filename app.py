import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yaml

from core.grid import Grid, GridState
from core.load import Hospital, Commercial, School, Residential
from core.renewable import SolarPV
from core.controller import CentralController
from utils.logger import SimulationLogger
from utils.constants import LoadType, PRIORITY_LEVELS

logger = SimulationLogger("Dashboard")

@st.cache_resource
def load_config():
    with open('config/simulation_config.yaml', 'r') as f:
        return yaml.safe_load(f)

config = load_config()

st.set_page_config(page_title="⚡ Smart Grid Game", page_icon="⚡", layout="wide")

st.title("⚡ Smart Grid Power Management Game")
st.markdown("**Manage electricity for 24 hours! Can you keep everyone's lights on?** 🎮")

# ========== SIDEBAR CONTROLS ==========
st.sidebar.title("⚙️ GAME SETTINGS")

grid_capacity = st.sidebar.slider("⚡ Power Plant Size (kW)", 1000, 5000, 2000, 500)
solar_capacity = st.sidebar.slider("☀️ Solar Panels (kW)", 0, 1000, 500, 100)
battery_capacity = st.sidebar.slider("🔋 Battery Size (kWh)", 50, 500, 200, 50)
base_price = st.sidebar.slider("💰 Base Price ($/MWh)", 50, 200, 100, 10)

st.sidebar.subheader("Load Flexibility")
hospital_flex = st.sidebar.slider("🏥 Hospital Can Reduce", 0.0, 0.2, 0.05, 0.01)
commercial_flex = st.sidebar.slider("🏢 Stores Can Reduce", 0.0, 0.3, 0.15, 0.01)
school_flex = st.sidebar.slider("🏫 School Can Reduce", 0.0, 0.4, 0.20, 0.01)
residential_flex = st.sidebar.slider("🏠 Homes Can Reduce", 0.0, 0.5, 0.30, 0.01)

# ========== SIMULATION FUNCTION ==========
def run_game():
    grid = Grid(main_generation_kw=grid_capacity, battery_capacity_kwh=battery_capacity)
    
    hospital = Hospital()
    hospital.flexibility = hospital_flex
    commercial = Commercial()
    commercial.flexibility = commercial_flex
    school = School()
    school.flexibility = school_flex
    residential = Residential()
    residential.flexibility = residential_flex
    
    loads = {
        LoadType.HOSPITAL: hospital,
        LoadType.COMMERCIAL: commercial,
        LoadType.SCHOOL: school,
        LoadType.RESIDENTIAL: residential,
    }
    
    solar = SolarPV(capacity_kw=solar_capacity)
    controller = CentralController()
    
    history = []
    
    for hour in range(24):
        for load_type, load in loads.items():
            load.calculate_demand(hour, stochastic=True)
        
        solar_gen = solar.calculate_generation(hour, stochastic=True)
        main_gen = grid.main_generation_kw * 0.85
        
        total_gen_with_battery = main_gen + solar_gen
        total_demand = sum(l.current_demand_kw for l in loads.values())
        sdr = grid.calculate_sdr(total_gen_with_battery, total_demand)
        
        battery_discharge, soc = grid.manage_battery(total_gen_with_battery, total_demand)
        total_gen = total_gen_with_battery + battery_discharge
        
        allocation = controller.allocate_energy_priority_based(total_gen, loads)
        
        if sdr < 0.85:
            shedding = controller.perform_load_shedding(loads, sdr)
        
        total_allocated = 0
        for load_type, load in loads.items():
            load.allocate_power(allocation[load_type])
            total_allocated += load.allocated_kw
        
        price = controller.calculate_sdr_based_price(sdr, base_price)
        
        for load in loads.values():
            load.update_cost(price)
        
        history.append({
            'hour': hour,
            'generation': total_gen,
            'solar': solar_gen,
            'demand': total_demand,
            'allocated': total_allocated,
            'sdr': sdr,
            'price': price,
            'battery_soc': soc,
            'hospital_demand': loads[LoadType.HOSPITAL].current_demand_kw,
            'hospital_allocated': loads[LoadType.HOSPITAL].allocated_kw,
            'commercial_demand': loads[LoadType.COMMERCIAL].current_demand_kw,
            'commercial_allocated': loads[LoadType.COMMERCIAL].allocated_kw,
            'school_demand': loads[LoadType.SCHOOL].current_demand_kw,
            'school_allocated': loads[LoadType.SCHOOL].allocated_kw,
            'residential_demand': loads[LoadType.RESIDENTIAL].current_demand_kw,
            'residential_allocated': loads[LoadType.RESIDENTIAL].allocated_kw,
        })
    
    return pd.DataFrame(history), loads, grid, controller

if st.sidebar.button("▶️ START SIMULATION!", key="run_sim"):
    with st.spinner("⏳ Running 24-hour simulation..."):
        df_history, loads, grid, controller = run_game()
        st.session_state.df_history = df_history
        st.session_state.loads = loads

if hasattr(st.session_state, 'df_history'):
    df = st.session_state.df_history
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "📈 GRAPHS", "📄 DATA", "ℹ️ HELP"])
    
    with tab1:
        st.subheader("⚡ POWER STATUS")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Peak Power Needed", f"{df['demand'].max():.0f} kW")
        with col2:
            st.metric("Avg SDR", f"{df['sdr'].mean():.2f}")
        with col3:
            st.metric("Avg Price", f"${df['price'].mean():.2f}")
        with col4:
            st.metric("Battery Left", f"{df['battery_soc'].iloc[-1]*100:.1f}%")
        
        st.subheader("⚡ Power Over 24 Hours")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['hour'], y=df['generation'], name='⚡ Power Made', mode='lines+markers', line=dict(color='green', width=4)))
        fig1.add_trace(go.Scatter(x=df['hour'], y=df['demand'], name='📊 Power Needed', mode='lines+markers', line=dict(color='red', width=4)))
        fig1.update_layout(xaxis_title="Hour", yaxis_title="Power (kW)", height=400, template='plotly_dark')
        st.plotly_chart(fig1, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💰 Price Over Time")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df['hour'], y=df['price'], name='Price', mode='lines+markers', line=dict(color='purple', width=3), fill='tozeroy'))
            fig2.update_layout(xaxis_title="Hour", yaxis_title="$/MWh", height=350, template='plotly_dark')
            st.plotly_chart(fig2, use_container_width=True)
        
        with col2:
            st.subheader("📊 Supply-Demand Ratio")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df['hour'], y=df['sdr'], name='SDR', mode='lines+markers', line=dict(color='orange', width=3), fill='tozeroy'))
            fig3.add_hline(y=1.0, line_dash="dash", line_color="white")
            fig3.update_layout(xaxis_title="Hour", yaxis_title="Ratio", height=350, template='plotly_dark')
            st.plotly_chart(fig3, use_container_width=True)
    
    with tab2:
        st.subheader("Load Demand vs Allocation")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Power Needed")
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(x=df['hour'], y=df['hospital_demand'], name='🏥 Hospital', mode='lines', stackgroup='one'))
            fig5.add_trace(go.Scatter(x=df['hour'], y=df['commercial_demand'], name='🏢 Commercial', mode='lines', stackgroup='one'))
            fig5.add_trace(go.Scatter(x=df['hour'], y=df['school_demand'], name='🏫 School', mode='lines', stackgroup='one'))
            fig5.add_trace(go.Scatter(x=df['hour'], y=df['residential_demand'], name='🏠 Residential', mode='lines', stackgroup='one'))
            fig5.update_layout(xaxis_title="Hour", yaxis_title="kW", height=400, template='plotly_dark')
            st.plotly_chart(fig5, use_container_width=True)
        
        with col2:
            st.subheader("Power Got")
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=df['hour'], y=df['hospital_allocated'], name='🏥 Hospital', mode='lines', stackgroup='one'))
            fig6.add_trace(go.Scatter(x=df['hour'], y=df['commercial_allocated'], name='🏢 Commercial', mode='lines', stackgroup='one'))
            fig6.add_trace(go.Scatter(x=df['hour'], y=df['school_allocated'], name='🏫 School', mode='lines', stackgroup='one'))
            fig6.add_trace(go.Scatter(x=df['hour'], y=df['residential_allocated'], name='🏠 Residential', mode='lines', stackgroup='one'))
            fig6.update_layout(xaxis_title="Hour", yaxis_title="kW", height=400, template='plotly_dark')
            st.plotly_chart(fig6, use_container_width=True)
    
    with tab3:
        st.subheader("📥 Download Data")
        csv = df.to_csv(index=False)
        st.download_button(label="📥 Download CSV", data=csv, file_name="power-game.csv", mime="text/csv")
        st.dataframe(df.round(2), use_container_width=True)
    
    with tab4:
        st.markdown("""
        ## 🎮 How to Play
        
        **GOAL:** Keep everyone's lights on for 24 hours!
        
        ### Use the sliders:
        - Power Plant = How much power you can make
        - Solar = Bonus power from sun
        - Battery = Store extra power for later
        - Price = Cost per unit
        
        ### Priority Order:
        1. 🏥 Hospital (MUST HAVE POWER!)
        2. 🏢 Stores
        3. 🏫 School
        4. 🏠 Homes
        
        ### Rules:
        - GREEN line = Power you made
        - RED line = Power needed
        - When power is LOW → Price goes UP! 💰
        - When power is HIGH → Price goes DOWN! 💵
        """)

else:
    st.info("👉 Click ▶️ START SIMULATION on the left!")