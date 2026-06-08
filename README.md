# looped_in

A vehicle dynamics control-system simulation designed to test AI-driven root-cause analysis.

## Overview

The repository contains a Python simulation of a vehicle performing the following sequence:

1. **Release the Electronic Park Brake (EPB)**
2. **Accelerate** from rest to a target speed (30 mph) under full throttle
3. **Maintain** that target speed using closed-loop hydraulic braking

Three software controllers manage the vehicle:

| Controller | Module | Responsibility |
|---|---|---|
| Park Brake | `simulation/controllers/park_brake.py` | EPB engage/release, residual torque |
| Powertrain | `simulation/controllers/powertrain.py` | Engine torque, gear selection, drive force |
| Brakes | `simulation/controllers/brakes.py` | PI speed regulation via hydraulic braking |

Vehicle physics (mass, aero drag, integrator) live in `simulation/vehicle.py`.

## Known Issues

Four bugs have been injected across the three controllers.  Each bug is documented in [`issues.json`](issues.json) as a realistic software defect report — complete with reproduction steps, telemetry data, and team conversation threads — but without disclosing the root cause directly.

The bugs are intended to exercise an AI agent's ability to:
- Reason from symptom descriptions and logged data
- Consult specialist sub-agents for controller-specific expertise
- Isolate root causes across interacting subsystems

## Running the Simulation

```bash
# From the repository root
python -m simulation.run_simulation
```

Requires Python 3.9+. No external dependencies.

## Repository Structure

```
looped_in/
├── issues.json                          # Bug reports (4 open issues)
├── simulation/
│   ├── vehicle.py                       # Vehicle physics model
│   ├── run_simulation.py                # Main simulation entry point
│   └── controllers/
│       ├── park_brake.py                # EPB controller  (contains Bug 1)
│       ├── powertrain.py                # Powertrain controller (Bugs 2 & 3)
│       └── brakes.py                    # Brake speed controller (Bug 4)
└── README.md
```