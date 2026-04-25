"""Renewable energy generation models."""

from enum import Enum
import numpy as np
from utils.constants import SOLAR_PROFILE, SOLAR_UNCERTAINTY, WIND_UNCERTAINTY
from utils.logger import SimulationLogger

logger = SimulationLogger("Renewable")

class SolarPV:
    """Solar Photovoltaic generation system."""
    
    def __init__(self, capacity_kw: float = 500.0):
        self.capacity_kw = capacity_kw
        self.cumulative_generation_kwh = 0.0
        
    def calculate_generation(self, hour: int, stochastic: bool = True) -> float:
        """
        Calculate solar generation for given hour.
        
        Args:
            hour: Hour of day (0-23)
            stochastic: Add ±15% random variation
            
        Returns:
            Generation in kW
        """
        profile_factor = SOLAR_PROFILE[hour % 24]
        base_generation = self.capacity_kw * profile_factor
        
        if stochastic:
            # Add cloud variation (±15%)
            variation = np.random.normal(0, SOLAR_UNCERTAINTY)
            base_generation *= (1 + variation)
        
        return max(0, base_generation)
    
    def get_capacity_factor(self, generation_kw: float) -> float:
        """Calculate capacity factor."""
        return generation_kw / self.capacity_kw if self.capacity_kw > 0 else 0.0

class WindTurbine:
    """Wind turbine generation system."""
    
    def __init__(self, 
                 capacity_kw: float = 1000.0,
                 cut_in_speed: float = 3.0,
                 cut_out_speed: float = 25.0):
        """
        Initialize wind turbine.
        
        Args:
            capacity_kw: Rated capacity
            cut_in_speed: Minimum wind speed (m/s)
            cut_out_speed: Maximum wind speed (m/s)
        """
        self.capacity_kw = capacity_kw
        self.cut_in_speed = cut_in_speed
        self.cut_out_speed = cut_out_speed
    
    def power_curve(self, wind_speed: float) -> float:
        """Calculate power output from wind speed using cubic curve."""
        if wind_speed < self.cut_in_speed or wind_speed > self.cut_out_speed:
            return 0.0
        
        # Cubic power curve approximation
        normalized_speed = (wind_speed - self.cut_in_speed) / (self.cut_out_speed - self.cut_in_speed)
        power_factor = normalized_speed ** 3
        return min(self.capacity_kw, self.capacity_kw * power_factor)
    
    def calculate_generation(self, wind_speed: float = 8.0, stochastic: bool = True) -> float:
        """Calculate wind generation."""
        if stochastic:
            variation = np.random.normal(0, WIND_UNCERTAINTY)
            wind_speed *= (1 + variation)
        
        return max(0, self.power_curve(wind_speed))

class HybridRenewable:
    """Combines solar and wind generation."""
    
    def __init__(self, solar_capacity: float = 500.0, wind_capacity: float = 0.0):
        self.solar = SolarPV(solar_capacity)
        self.wind = WindTurbine(wind_capacity) if wind_capacity > 0 else None
    
    def calculate_generation(self, hour: int, wind_speed: float = 8.0) -> float:
        """Calculate total renewable generation."""
        solar_gen = self.solar.calculate_generation(hour)
        wind_gen = self.wind.calculate_generation(wind_speed) if self.wind else 0.0
        return solar_gen + wind_gen