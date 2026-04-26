"""
Load models for different consumer types.
Implements priority-based allocation and demand response.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import numpy as np
from utils.constants import (
    LoadType, LoadStatus, LOAD_PROFILES, 
    PRIORITY_LEVELS
)
from utils.logger import SimulationLogger

logger = SimulationLogger("Load")

class Load:
    """Base load class."""
    
    def __init__(self, 
                 load_type: LoadType,
                 demand_kw: float,
                 flexibility: float = 0.1):
        """
        Initialize load.
        
        Args:
            load_type: Type of load (Hospital, Commercial, etc.)
            demand_kw: Peak demand in kW
            flexibility: Flexibility ratio (0-1, higher = more flexible)
        """
        self.load_type = load_type
        self.peak_demand_kw = demand_kw
        self.flexibility = flexibility
        self.priority = PRIORITY_LEVELS[load_type]
        
        # Custom 24-hour demand profile (absolute kW values).
        # When set, overrides the default LOAD_PROFILES factor-based calculation.
        self.custom_profile: Optional[List[float]] = None
        
        # Current state
        self.current_demand_kw = 0.0
        self.allocated_kw = 0.0
        self.shed_kw = 0.0
        self.status = LoadStatus.ACTIVE
        self.hourly_cost = 0.0
        
        # Cost tracking
        self.cumulative_cost = 0.0
        self.cumulative_energy_kwh = 0.0
        self.shedding_events = 0
        
    def set_custom_profile(self, profile: List[float]):
        """
        Set a custom 24-hour absolute demand profile (kW per hour).
        
        Args:
            profile: List of 24 demand values in kW (one per hour).
        """
        if len(profile) != 24:
            raise ValueError("Custom profile must have exactly 24 values.")
        self.custom_profile = list(profile)

    def calculate_demand(self, hour: int, stochastic: bool = True) -> float:
        """
        Calculate demand for given hour.
        
        If a custom_profile has been set, it is used directly (absolute kW).
        Otherwise the default LOAD_PROFILES factor is applied to peak_demand_kw.
        
        Args:
            hour: Hour of day (0-23)
            stochastic: Add ±5% random variation
            
        Returns:
            Demand in kW
        """
        if self.custom_profile is not None:
            base_demand = self.custom_profile[hour % 24]
        else:
            profile_factor = LOAD_PROFILES[self.load_type][hour % 24]
            base_demand = self.peak_demand_kw * profile_factor
        
        if stochastic:
            variation = np.random.normal(0, 0.05)  # ±5% std dev
            base_demand *= (1 + variation)
        
        self.current_demand_kw = max(0, base_demand)
        return self.current_demand_kw
    
    def allocate_power(self, allocated_kw: float) -> float:
        """
        Allocate power to this load.
        
        Args:
            allocated_kw: Power allocated in kW
            
        Returns:
            Actual power allocated
        """
        self.allocated_kw = min(allocated_kw, self.current_demand_kw)
        self.shed_kw = self.current_demand_kw - self.allocated_kw
        
        # Determine status
        if self.shed_kw == 0:
            self.status = LoadStatus.ACTIVE
        elif self.allocated_kw >= self.current_demand_kw * 0.5:
            self.status = LoadStatus.PARTIAL_SHED
        else:
            self.status = LoadStatus.FULL_SHED
        
        return self.allocated_kw
    
    def update_cost(self, price_per_mwh: float) -> float:
        """
        Update cumulative cost based on allocated power (1-hour timestep).
        
        Args:
            price_per_mwh: Current price in RS/MWh
            
        Returns:
            Hourly cost in RS
        """
        # Timestep = 1 hour: energy (MWh) = allocated_kw × 1 h ÷ 1000
        energy_mwh = (self.allocated_kw * 1.0) / 1000.0
        cost = energy_mwh * price_per_mwh
        
        self.hourly_cost = cost
        self.cumulative_cost += cost
        self.cumulative_energy_kwh += self.allocated_kw * 1.0  # kW × 1 h = kWh
        return cost
    
    def handle_shedding(self, shedding_rate: float) -> float:
        """Handle load shedding with flexibility constraints."""
        max_shed = self.peak_demand_kw * self.flexibility
        shed_amount = min(max_shed * shedding_rate, self.current_demand_kw)
        self.shedding_events += 1
        logger.warning(f"Load shedding: {self.load_type.value} at {shedding_rate*100:.1f}%")
        return shed_amount

class Hospital(Load):
    """Hospital load - Critical, highest priority."""
    
    def __init__(self, demand_kw: float = 300.0):
        super().__init__(LoadType.HOSPITAL, demand_kw, flexibility=0.05)
        self.min_load = 0.80  # Must supply 80% minimum
        logger.info("🏥 Hospital load initialized: 300 kW, Priority 1 (highest)")

class Commercial(Load):
    """Commercial load - Business hours pattern."""
    
    def __init__(self, demand_kw: float = 600.0):
        super().__init__(LoadType.COMMERCIAL, demand_kw, flexibility=0.15)
        self.min_load = 0.75
        logger.info("🏢 Commercial load initialized: 600 kW, Priority 2")

class School(Load):
    """School load - School hours pattern."""
    
    def __init__(self, demand_kw: float = 200.0):
        super().__init__(LoadType.SCHOOL, demand_kw, flexibility=0.20)
        self.min_load = 0.70
        logger.info("🏫 School load initialized: 200 kW, Priority 3")

class Residential(Load):
    """Residential load - Evening/morning peaks."""
    
    def __init__(self, demand_kw: float = 2000.0):
        super().__init__(LoadType.RESIDENTIAL, demand_kw, flexibility=0.30)
        self.min_load = 0.60
        logger.info("🏠 Residential load initialized: 2000 kW, Priority 4")

class Home1(Load):
    """Home 1 - Residential household load."""
    
    def __init__(self, demand_kw: float = 500.0):
        super().__init__(LoadType.HOME1, demand_kw, flexibility=0.30)
        self.min_load = 0.60
        logger.info(f"🏠 Home 1 load initialized: {demand_kw} kW, Priority 4")

class Home2(Load):
    """Home 2 - Residential household load."""
    
    def __init__(self, demand_kw: float = 500.0):
        super().__init__(LoadType.HOME2, demand_kw, flexibility=0.30)
        self.min_load = 0.60
        logger.info(f"🏠 Home 2 load initialized: {demand_kw} kW, Priority 5")

class Home3(Load):
    """Home 3 - Residential household load."""
    
    def __init__(self, demand_kw: float = 500.0):
        super().__init__(LoadType.HOME3, demand_kw, flexibility=0.30)
        self.min_load = 0.60
        logger.info(f"🏠 Home 3 load initialized: {demand_kw} kW, Priority 6")