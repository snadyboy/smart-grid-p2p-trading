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
        
        # Current state
        self.current_demand_kw = 0.0
        self.allocated_kw = 0.0
        self.shed_kw = 0.0
        self.status = LoadStatus.ACTIVE
        
        # Cost tracking
        self.cumulative_cost = 0.0
        self.cumulative_energy_kwh = 0.0
        self.shedding_events = 0
        
    def calculate_demand(self, hour: int, stochastic: bool = True) -> float:
        """
        Calculate demand for given hour.
        
        Args:
            hour: Hour of day (0-23)
            stochastic: Add ±10% random variation
            
        Returns:
            Demand in kW
        """
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
    
    def update_cost(self, price_per_mwh: float):
        """
        Update cumulative cost based on allocated power.
        
        Args:
            price_per_mwh: Current price in $/MWh
        """
        # Energy in MWh for 1-minute timestep
        energy_mwh = (self.allocated_kw / 1000.0) / 60.0
        cost = energy_mwh * price_per_mwh
        
        self.cumulative_cost += cost
        self.cumulative_energy_kwh += self.allocated_kw / 60.0
    
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
        logger.info("🏥 Hospital load initialized: 300 kW, Priority 4")

class Commercial(Load):
    """Commercial load - Business hours pattern."""
    
    def __init__(self, demand_kw: float = 600.0):
        super().__init__(LoadType.COMMERCIAL, demand_kw, flexibility=0.15)
        self.min_load = 0.75
        logger.info("🏢 Commercial load initialized: 600 kW, Priority 3")

class School(Load):
    """School load - School hours pattern."""
    
    def __init__(self, demand_kw: float = 200.0):
        super().__init__(LoadType.SCHOOL, demand_kw, flexibility=0.20)
        self.min_load = 0.70
        logger.info("🏫 School load initialized: 200 kW, Priority 2")

class Residential(Load):
    """Residential load - Evening/morning peaks."""
    
    def __init__(self, demand_kw: float = 2000.0):
        super().__init__(LoadType.RESIDENTIAL, demand_kw, flexibility=0.30)
        self.min_load = 0.60
        logger.info("🏠 Residential load initialized: 2000 kW, Priority 1")