# ⚡ Smart Grid P2P Energy Trading Simulator

## Overview

This is an **interactive game-like simulator** for managing a smart power grid with:
- 🏥 Hospitals (critical load)
- 🏢 Commercial buildings
- 🏫 Schools
- 🏠 Residential homes
- ☀️ Solar power generation
- 🔋 Battery storage
- 💰 Dynamic pricing based on supply/demand

## Quick Start

### 1. Install Python 3.9+
Download from: https://www.python.org/

### 2. Extract Files
Download this project and extract to a folder: `smart-grid-p2p-trading`

### 3. Install Dependencies
```bash
cd smart-grid-p2p-trading
pip install -r requirements.txt
```

### 4. Run the Simulator
```bash
streamlit run app.py
```

### 5. Open in Browser
Go to: `http://localhost:8501`

## How It Works

### The Game
1. **Adjust sliders** to control:
   - Power plant size
   - Solar panel capacity
   - Battery size
   - Electricity price

2. **Click "START SIMULATION"** to run 24 hours

3. **Watch the charts** showing:
   - Power generation vs demand
   - Price changes throughout the day
   - Supply-Demand Ratio (SDR)
   - Battery state of charge

### Key Concepts

**Priority-Based Allocation:**
- Hospital gets power FIRST (highest priority)
- Commercial buildings get power second
- Schools get power third
- Homes get power last

**Dynamic Pricing:**
- Excess power (SDR > 1.5) → 50% discount
- Normal (SDR 0.9-1.5) → Normal price
- Shortage (SDR < 0.9) → 2-3× price

**Battery Management:**
- Charges when power is abundant
- Discharges when power is scarce
- 92% efficiency
- 200 kWh capacity

## System Architecture

```
config/
  └─ simulation_config.yaml    (Game settings)
  
core/
  ├─ grid.py                   (Power grid)
  ├─ load.py                   (Hospitals, schools, homes, etc)
  ├─ renewable.py              (Solar panels)
  ├─ storage.py                (Battery)
  └─ controller.py             (Decision maker)
  
utils/
  ├─ constants.py              (Settings and profiles)
  └─ logger.py                 (Messages)
  
app.py                         (Main game interface)
```

## Technology Stack

- **Python 3.9+** - Programming language
- **Streamlit** - Interactive web interface
- **Plotly** - Charts and graphs
- **Pandas** - Data management
- **NumPy** - Numerical calculations

## Files Included

| File | Purpose |
|------|----------|
| `requirements.txt` | Install these Python packages |
| `config/simulation_config.yaml` | Game settings (power, loads, prices) |
| `core/grid.py` | Power grid management |
| `core/load.py` | Load models (Hospital, School, etc) |
| `core/renewable.py` | Solar generation |
| `core/storage.py` | Battery system |
| `core/controller.py` | Energy allocation & pricing |
| `utils/constants.py` | Settings & profiles |
| `utils/logger.py` | Message logging |
| `app.py` | **THE MAIN GAME** |

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt --upgrade
```

### "Port 8501 already in use"
```bash
streamlit run app.py --server.port 8502
```

### "YAML file not found"
Make sure folder structure is correct:
```
smart-grid-p2p-trading/
  ├─ config/
  │  └─ simulation_config.yaml
  ├─ core/
  ├─ utils/
  ├─ app.py
  └─ requirements.txt
```

## Game Tips

🔴 **If prices are too high:**
- Increase power plant size
- Add more solar panels
- Make battery bigger

💙 **If loads are getting cut off:**
- Look at residential loads (they're huge at peak hours!)
- Try reducing their flexibility

🔋 **To use battery better:**
- Increase battery size
- Increase solar capacity (more to store)

☀️ **To save money:**
- Add solar panels (free power at noon!)
- Watch the price drops at midday

## Based On Research

This simulator implements concepts from:
> "A decentralized peer-to-peer energy trading strategy considering flexible resource involvement and renewable energy uncertainty" by Wei Zhou et al.

Key features:
- Supply-Demand Ratio (SDR) pricing
- Flexible resource management
- Renewable uncertainty modeling
- Priority-based load allocation
- Decentralized control

## Next Steps

1. ✅ Run the simulator
2. ✅ Play with the sliders
3. ✅ Watch what happens over 24 hours
4. ✅ Try different configurations
5. ✅ Export data and analyze
6. 🔧 Add P2P trading features
7. 🔧 Add machine learning forecasting

## License

Open source - use freely!

## Questions?

Try adjusting different sliders to see how the system responds!
