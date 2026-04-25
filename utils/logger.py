"""Logging utilities for simulation."""

import logging
from datetime import datetime
from typing import Optional

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with console handler."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

class SimulationLogger:
    """Centralized logging for simulation."""
    
    def __init__(self, name: str = "SmartGrid"):
        self.logger = setup_logger(name)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def log_grid_state(self, sdr: float, price: float, gen: float, dem: float):
        self.info(f"SDR: {sdr:.2f} | Price: ${price:.2f}/MWh | Gen: {gen:.0f}kW | Dem: {dem:.0f}kW")
    
    def log_shedding_event(self, load_type: str, rate: float):
        self.warning(f"Load shedding: {load_type} at {rate*100:.1f}%")
    
    def log_battery_action(self, action: str, power: float, soc: float):
        self.info(f"Battery {action}: {power:.0f}kW | SOC: {soc*100:.1f}%")