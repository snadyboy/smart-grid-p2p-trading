"""
Constants and data structures for smart grid simulation.
Based on Zhou et al. - P2P energy trading with flexible resources.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
from datetime import datetime

# ============================================================================
# ENUMS
# ============================================================================

class LoadType(Enum):
    """Load type classification."""
    HOSPITAL = "hospital"
    COMMERCIAL = "commercial"
    SCHOOL = "school"
    RESIDENTIAL = "residential"
    HOME1 = "home1"
    HOME2 = "home2"
    HOME3 = "home3"

class LoadStatus(Enum):
    """Load operational status."""
    ACTIVE = "active"
    PARTIAL_SHED = "partial_shed"
    FULL_SHED = "full_shed"
    DISCONNECTED = "disconnected"

class GridState(Enum):
    """Grid operating state."""
    NORMAL = "normal"
    STRESSED = "stressed"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class RenewableType(Enum):
    """Renewable energy source type."""
    SOLAR = "solar"
    WIND = "wind"
    HYBRID = "hybrid"

# ============================================================================
# PRIORITY LEVELS
# ============================================================================

PRIORITY_LEVELS = {
    LoadType.HOSPITAL: 1,      # Highest (served first)
    LoadType.COMMERCIAL: 2,
    LoadType.SCHOOL: 3,
    LoadType.RESIDENTIAL: 4,
    LoadType.HOME1: 4,
    LoadType.HOME2: 5,
    LoadType.HOME3: 6,         # Lowest (served last)
}

# ============================================================================
# LOAD PROFILES (HOURLY PATTERNS)
# ============================================================================

LOAD_PROFILES = {
    LoadType.HOSPITAL: [
        0.90, 0.88, 0.85, 0.83, 0.82, 0.84, 0.88, 0.92, 0.95, 0.98,
        1.00, 0.99, 0.98, 0.97, 0.98, 0.99, 1.00, 0.99, 0.98, 0.97,
        0.95, 0.93, 0.91, 0.90
    ],
    LoadType.COMMERCIAL: [
        0.20, 0.15, 0.10, 0.08, 0.10, 0.15, 0.30, 0.60, 0.80, 0.95,
        0.98, 1.00, 0.99, 0.98, 0.97, 0.95, 0.90, 0.70, 0.50, 0.40,
        0.30, 0.25, 0.22, 0.20
    ],
    LoadType.SCHOOL: [
        0.10, 0.05, 0.05, 0.05, 0.08, 0.15, 0.40, 0.80, 0.95, 0.98,
        1.00, 0.99, 0.98, 0.97, 0.96, 0.95, 0.90, 0.50, 0.20, 0.15,
        0.12, 0.10, 0.08, 0.08
    ],
    LoadType.RESIDENTIAL: [
        0.40, 0.35, 0.32, 0.30, 0.32, 0.38, 0.50, 0.55, 0.48, 0.45,
        0.50, 0.55, 0.58, 0.60, 0.62, 0.60, 0.55, 0.65, 0.80, 0.90,
        0.95, 0.98, 0.85, 0.60
    ],
    LoadType.HOME1: [
        0.40, 0.35, 0.32, 0.30, 0.32, 0.38, 0.50, 0.55, 0.48, 0.45,
        0.50, 0.55, 0.58, 0.60, 0.62, 0.60, 0.55, 0.65, 0.80, 0.90,
        0.95, 0.98, 0.85, 0.60
    ],
    LoadType.HOME2: [
        0.35, 0.30, 0.28, 0.28, 0.30, 0.35, 0.45, 0.52, 0.50, 0.48,
        0.52, 0.58, 0.60, 0.62, 0.65, 0.63, 0.58, 0.68, 0.82, 0.92,
        0.96, 0.99, 0.88, 0.65
    ],
    LoadType.HOME3: [
        0.42, 0.38, 0.34, 0.32, 0.34, 0.40, 0.52, 0.58, 0.46, 0.44,
        0.48, 0.53, 0.56, 0.58, 0.60, 0.58, 0.53, 0.62, 0.78, 0.88,
        0.93, 0.96, 0.82, 0.58
    ],
}

# ============================================================================
# SOLAR GENERATION PROFILE (NORMALIZED)
# ============================================================================

SOLAR_PROFILE = [
    0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.15, 0.35, 0.55, 0.75,
    0.90, 0.95, 0.98, 0.95, 0.90, 0.75, 0.55, 0.35, 0.15, 0.05,
    0.00, 0.00, 0.00, 0.00
]

# ============================================================================
# CONSTANTS
# ============================================================================

# SDR Thresholds
SDR_THRESHOLD_HIGH = 1.5      # Surplus (excess generation)
SDR_THRESHOLD_NORMAL_HIGH = 0.9  # Normal (slight shortage)
SDR_THRESHOLD_NORMAL_LOW = 0.5   # Shortage (critical)

# Price Multipliers
PRICE_MULTIPLIER_EXCESS = 0.5      # 50% discount
PRICE_MULTIPLIER_SHORTAGE = 2.0    # 2× multiplier
PRICE_MULTIPLIER_CRITICAL = 3.0    # 3× multiplier

# Battery Parameters
BATTERY_EFFICIENCY = 0.92      # 92% round-trip
BATTERY_SOC_MIN = 0.20         # 20% minimum
BATTERY_SOC_MAX = 0.95         # 95% maximum
BATTERY_RESERVE = 0.30         # 30% emergency reserve

# Load Shedding
SHEDDING_THRESHOLD_SDR = 0.85  # Trigger at SDR < 0.85
SHEDDING_RATE = 0.25           # Shed 25% per step

# Renewable
SOLAR_UNCERTAINTY = 0.15       # ±15% variation
WIND_UNCERTAINTY = 0.20        # ±20% variation

# Base prices
BASE_PRICE_MWH = 100.0         # $/MWh