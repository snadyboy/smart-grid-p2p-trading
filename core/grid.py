"""
Grid management and coordination.
Central aggregation point for generation, storage, and loads.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import numpy as np
from utils.constants import SDR_THRESHOLD_HIGH, SDR_THRESHOLD_NORMAL_HIGH
from utils.logger import SimulationLogger

logger = SimulationLogger("Grid")

@dataclass
class GridState:
    """Snapshot of grid state at a point in time."""
    timestamp: str
    total_generation_kw: float = 0.0
    renewable_generation_kw: float = 0.0
    battery_discharge_kw: float = 0.0
    total_demand_kw: float = 0.0
    total_allocated_kw: float = 0.0
    total_shed_kw: float = 0.0
    battery_soc: float = 0.5
    sdr: float = 1.0
    price_per_mwh: float = 100.0
    grid_frequency: float = 50.0
    energy_balance_kwh: float = 0.0

class Grid:
    """Central grid controller managing all components."""
    
    def __init__(self, 
                 main_generation_kw: float = 2000.0,
                 battery_capacity_kwh: float = 200.0):
        """Initialize grid."""
        self.main_generation_kw = main_generation_kw
        self.battery_capacity_kwh = battery_capacity_kwh
        self.battery_soc = 0.5  # Start at 50%
        self.battery_efficiency = 0.92
        
        # Cumulative tracking
        self.cumulative_generation_kwh = 0.0
        self.cumulative_demand_kwh = 0.0
        self.cumulative_cost = 0.0
        
        # History
        self.history: List[GridState] = []
        
        # Frequency regulation
        self.nominal_frequency = 50.0  # Hz
        self.frequency_droop = 0.05  # Hz per unit MW deviation
        
    def calculate_sdr(self, generation_kw: float, demand_kw: float) -> float:
        """
        Calculate Supply-Demand Ratio (SDR).
        
        SDR = Generation / Demand
        SDR > 1.5: Excess generation (surplus)
        0.9 ≤ SDR ≤ 1.5: Normal operation
        0.5 < SDR < 0.9: Shortage
        SDR ≤ 0.5: Critical shortage
        """
        if demand_kw <= 0:
            return 2.0  # Assume normal if no demand
        return generation_kw / demand_kw
    
    def calculate_dynamic_price(self, sdr: float, base_price: float = 100.0) -> float:
        """
        Calculate dynamic price based on SDR.
        
        Args:
            sdr: Supply-Demand Ratio
            base_price: Base price in $/MWh
            
        Returns:
            Price in $/MWh
        """
        if sdr >= SDR_THRESHOLD_HIGH:  # Excess
            return base_price * 0.5  # 50% discount
        elif sdr >= SDR_THRESHOLD_NORMAL_HIGH:  # Normal
            return base_price * 1.0  # Normal price
        elif sdr >= 0.5:  # Shortage
            return base_price * 2.0  # 2× multiplier
        else:  # Emergency
            return base_price * 3.0  # 3× multiplier
    
    def update_grid_frequency(self, sdr: float) -> float:
        """
        Update grid frequency based on generation-demand balance.
        
        Lower generation → Lower frequency
        Higher generation → Higher frequency
        """
        frequency_deviation = (sdr - 1.0) * self.frequency_droop
        return self.nominal_frequency + frequency_deviation
    
    def manage_battery(self, 
                      generation_kw: float, 
                      demand_kw: float,
                      charge_threshold: float = 1.2,
                      discharge_threshold: float = 0.85) -> Tuple[float, float]:
        """
        Manage battery charge/discharge based on SDR.
        
        Returns:
            (battery_discharge_kw, new_soc)
        """
        sdr = self.calculate_sdr(generation_kw, demand_kw)
        
        battery_discharge_kw = 0.0
        new_soc = self.battery_soc
        
        if sdr >= charge_threshold and new_soc < 0.95:
            # Charge battery (surplus)
            charge_power = min(100.0, generation_kw - demand_kw)
            energy_added_kwh = (charge_power / 60.0) * self.battery_efficiency
            new_soc = min(0.95, new_soc + energy_added_kwh / self.battery_capacity_kwh)
            logger.info(f"🔋 Battery CHARGING: {charge_power:.0f}kW | SOC: {new_soc*100:.1f}%")
            
        elif sdr <= discharge_threshold and new_soc > 0.20:
            # Discharge battery (shortage)
            deficit = demand_kw - generation_kw
            discharge_power = min(100.0, deficit)
            energy_removed_kwh = (discharge_power / 60.0) / self.battery_efficiency
            new_soc = max(0.20, new_soc - energy_removed_kwh / self.battery_capacity_kwh)
            battery_discharge_kw = discharge_power
            logger.info(f"🔋 Battery DISCHARGING: {discharge_power:.0f}kW | SOC: {new_soc*100:.1f}%")
        
        self.battery_soc = new_soc
        return battery_discharge_kw, new_soc
    
    def record_state(self, state: GridState):
        """Record grid state snapshot."""
        self.history.append(state)
    
    def get_latest_state(self) -> GridState:
        """Get most recent grid state."""
        if self.history:
            return self.history[-1]
        return GridState(timestamp=datetime.now().isoformat())