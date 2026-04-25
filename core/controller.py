"""
Central controller for energy allocation, pricing, and load shedding.
Based on Zhou et al. - P2P energy trading with decentralized control.
"""

from typing import Dict, List, Tuple
from utils.constants import (
    LoadType, PRIORITY_LEVELS,
    SDR_THRESHOLD_HIGH, SDR_THRESHOLD_NORMAL_HIGH,
    SHEDDING_THRESHOLD_SDR, SHEDDING_RATE
)
from utils.logger import SimulationLogger

logger = SimulationLogger("Controller")

class CentralController:
    """Central grid controller implementing allocation and pricing."""
    
    def __init__(self):
        self.shedding_history = []
        self.trading_log = []
    
    def allocate_energy_priority_based(self, 
                                      total_generation_kw: float,
                                      loads: Dict) -> Dict:
        """
        Allocate energy based on priority.
        
        Priority Order: Hospital (4) → Commercial (3) → School (2) → Residential (1)
        
        Args:
            total_generation_kw: Available generation
            loads: Dictionary of load objects
            
        Returns:
            Dictionary of allocated power per load type
        """
        allocation = {}
        remaining_generation = total_generation_kw
        
        # Sort by priority (highest first)
        sorted_loads = sorted(loads.items(), 
                            key=lambda x: PRIORITY_LEVELS[x[0]], 
                            reverse=True)
        
        for load_type, load in sorted_loads:
            demand = load.current_demand_kw
            allocated = min(remaining_generation, demand)
            allocation[load_type] = allocated
            remaining_generation -= allocated
            
            if remaining_generation <= 0:
                break
        
        # Ensure all loads have an allocation
        for load_type, load in loads.items():
            if load_type not in allocation:
                allocation[load_type] = 0.0
        
        logger.info(f"⚡ Allocation: Hospital={allocation[LoadType.HOSPITAL]:.0f}kW, "
                   f"Commercial={allocation[LoadType.COMMERCIAL]:.0f}kW, "
                   f"School={allocation[LoadType.SCHOOL]:.0f}kW, "
                   f"Residential={allocation[LoadType.RESIDENTIAL]:.0f}kW")
        
        return allocation
    
    def perform_load_shedding(self,
                             loads: Dict,
                             sdr: float) -> Dict:
        """
        Perform intelligent load shedding based on priority.
        
        Args:
            loads: Dictionary of load objects
            sdr: Current supply-demand ratio
            
        Returns:
            Shedding amounts per load type
        """
        shedding_amounts = {}
        
        if sdr >= SHEDDING_THRESHOLD_SDR:
            # No shedding needed
            return {lt: 0.0 for lt in loads.keys()}
        
        # Shed in REVERSE priority order (lowest priority first)
        sorted_loads = sorted(loads.items(),
                            key=lambda x: PRIORITY_LEVELS[x[0]],
                            reverse=False)
        
        for load_type, load in sorted_loads:
            if sdr >= SHEDDING_THRESHOLD_SDR:
                break
            
            # Shed up to flexibility limit
            shed_amount = load.handle_shedding(SHEDDING_RATE)
            shedding_amounts[load_type] = shed_amount
        
        return shedding_amounts
    
    def calculate_sdr_based_price(self,
                                  sdr: float,
                                  base_price: float = 100.0) -> float:
        """
        Calculate dynamic price based on SDR.
        
        Args:
            sdr: Supply-Demand Ratio
            base_price: Base price in $/MWh
            
        Returns:
            Dynamic price in $/MWh
        """
        if sdr >= SDR_THRESHOLD_HIGH:  # Excess (>150%)
            price = base_price * 0.5
            logger.info(f"💰 Excess: SDR={sdr:.2f}, Price=${price:.2f}/MWh (50% OFF)")
        elif sdr >= SDR_THRESHOLD_NORMAL_HIGH:  # Normal (90-150%)
            price = base_price * 1.0
            logger.info(f"💰 Normal: SDR={sdr:.2f}, Price=${price:.2f}/MWh")
        elif sdr >= 0.5:  # Shortage (50-90%)
            price = base_price * 2.0
            logger.warning(f"⚠️ Shortage: SDR={sdr:.2f}, Price=${price:.2f}/MWh (2×)")
        else:  # Emergency (<50%)
            price = base_price * 3.0
            logger.error(f"🚨 CRITICAL: SDR={sdr:.2f}, Price=${price:.2f}/MWh (3×)")
        
        return price
    
    def log_p2p_trade(self, buyer: str, seller: str, power_kw: float, price: float):
        """Log P2P trading transaction."""
        trade = {
            'buyer': buyer,
            'seller': seller,
            'power_kw': power_kw,
            'price': price,
        }
        self.trading_log.append(trade)
        logger.info(f"💱 P2P Trade: {buyer} buys {power_kw:.0f}kW from {seller} at ${price:.2f}/MWh")