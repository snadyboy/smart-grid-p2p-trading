"""
Central controller for energy allocation, pricing, and load shedding.
Based on Zhou et al. - P2P energy trading with decentralized control.
"""

from typing import Dict, List, Tuple
from utils.constants import (
    LoadType,
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
        
        Loads are served in ascending priority order (priority 1 = highest).
        Each load's priority is read from load.priority.
        
        Args:
            total_generation_kw: Available generation
            loads: Dictionary of load objects
            
        Returns:
            Dictionary of allocated power per load type
        """
        allocation = {}
        remaining_generation = total_generation_kw
        
        # Sort by priority ascending: lowest number = highest priority = served first
        sorted_loads = sorted(loads.items(), 
                            key=lambda x: x[1].priority,
                            reverse=False)
        
        for load_type, load in sorted_loads:
            demand = load.current_demand_kw
            allocated = min(remaining_generation, demand)
            allocation[load_type] = allocated
            remaining_generation = max(0.0, remaining_generation - allocated)
        
        # Ensure all loads have an allocation entry
        for load_type in loads:
            if load_type not in allocation:
                allocation[load_type] = 0.0
        
        alloc_str = ", ".join(
            f"{lt.value}={v:.0f}kW" for lt, v in allocation.items()
        )
        logger.info(f"⚡ Allocation: {alloc_str}")
        
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
        
        # Shed in REVERSE priority order (lowest priority = highest number first)
        sorted_loads = sorted(loads.items(),
                            key=lambda x: x[1].priority,
                            reverse=True)
        
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