"""Energy storage (battery) system."""

from dataclasses import dataclass
import numpy as np
from utils.logger import SimulationLogger

logger = SimulationLogger("Storage")

class Battery:
    """Lithium-ion battery energy storage system."""
    
    def __init__(self, 
                 capacity_kwh: float = 200.0,
                 efficiency: float = 0.92,
                 max_power_kw: float = 100.0):
        """
        Initialize battery.
        
        Args:
            capacity_kwh: Total energy capacity
            efficiency: Round-trip efficiency (0-1)
            max_power_kw: Max charge/discharge rate
        """
        self.capacity_kwh = capacity_kwh
        self.efficiency = efficiency
        self.max_power_kw = max_power_kw
        
        self.soc = 0.5  # Start at 50%
        self.cycle_count = 0
        self.degradation = 0.0
        
    def charge(self, power_kw: float, duration_minutes: float = 1.0) -> float:
        """Charge battery."""
        actual_power = min(power_kw, self.max_power_kw)
        energy_in_kwh = (actual_power * duration_minutes / 60.0) * self.efficiency
        
        new_soc = min(0.95, self.soc + energy_in_kwh / self.capacity_kwh)
        delta_soc = new_soc - self.soc
        self.soc = new_soc
        
        return actual_power
    
    def discharge(self, power_kw: float, duration_minutes: float = 1.0) -> float:
        """Discharge battery."""
        actual_power = min(power_kw, self.max_power_kw)
        energy_out_kwh = (actual_power * duration_minutes / 60.0) / self.efficiency
        
        new_soc = max(0.20, self.soc - energy_out_kwh / self.capacity_kwh)
        self.soc = new_soc
        
        return actual_power
    
    def get_available_energy_kwh(self) -> float:
        """Get available energy for discharge."""
        return self.capacity_kwh * (self.soc - 0.20)