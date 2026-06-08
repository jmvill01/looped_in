"""
run_simulation.py — Vehicle Dynamics Control System simulation entry point.

Scenario
--------
1. Vehicle starts stationary with the Electronic Park Brake (EPB) engaged.
2. The EPB is commanded to release.
3. The powertrain is placed in Drive and throttle is applied to accelerate
   toward TARGET_SPEED_MPH (30 mph).
4. Once the target speed is reached, the brake controller takes over to
   maintain that speed by modulating hydraulic brake force.

Known issues affect this simulation — see ``issues.json`` for filed reports.

Usage
-----
    python -m simulation.run_simulation
    # or
    python simulation/run_simulation.py
"""

from simulation.vehicle import VehicleState
from simulation.controllers.park_brake import ParkBrakeController
from simulation.controllers.powertrain import PowertrainController, WHEEL_RADIUS_M
from simulation.controllers.brakes import BrakesController

# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------

TARGET_SPEED_MPH: float = 30.0    # Desired cruise / hold speed
DT: float = 0.05                  # Timestep (s) — 50 ms
DURATION: float = 120.0           # Total run time (s)
LOG_INTERVAL: float = 1.0         # Console print interval (s)

# ---------------------------------------------------------------------------
# Phase thresholds
# ---------------------------------------------------------------------------

ACCEL_DEADBAND_MPH: float = 1.0   # Drop throttle within this band of target

# ---------------------------------------------------------------------------
# Simulation phases
# ---------------------------------------------------------------------------

PHASE_PARK  = "PARK_BRAKE_ENGAGED"
PHASE_ACCEL = "ACCELERATING"
PHASE_HOLD  = "HOLDING_SPEED"


def run() -> None:
    """Execute the full vehicle simulation and print a telemetry table."""

    # ---- Initialise subsystems ----------------------------------------
    state       = VehicleState()
    park_brake  = ParkBrakeController()
    powertrain  = PowertrainController()
    brakes      = BrakesController()

    brakes.set_target_speed(TARGET_SPEED_MPH)

    # ---- Step 1 : release park brake ---------------------------------
    print("=" * 72)
    print("  Vehicle Dynamics Control System — Simulation")
    print(f"  Target speed : {TARGET_SPEED_MPH:.0f} mph")
    print("=" * 72)
    print()
    print("[SIM] Step 1 — Commanding EPB release...")
    park_brake.release()
    print(f"      EPB engaged     : {park_brake.is_engaged}")
    print(f"      EPB hold torque : {park_brake.get_braking_torque():.1f} Nm")
    print()

    # ---- Step 2 : select Drive, enable powertrain --------------------
    print("[SIM] Step 2 — Selecting Drive range...")
    powertrain.request_drive()
    print()

    # ---- Telemetry header --------------------------------------------
    header = (
        f"{'Time(s)':>8}  {'Speed(mph)':>10}  {'Accel(m/s²)':>12}  "
        f"{'Gear':>5}  {'RPM':>6}  {'Throttle':>9}  "
        f"{'BrakeF(N)':>10}  {'PB_Torq(Nm)':>12}  {'Phase':>18}"
    )
    print(header)
    print("-" * len(header))

    phase = PHASE_ACCEL
    next_log = 0.0

    # ---- Main simulation loop ----------------------------------------
    while state.elapsed_time <= DURATION:
        speed_mph = state.speed_mph
        speed_ms  = state.speed_ms
        t         = state.elapsed_time

        # -- Determine phase -------------------------------------------
        if speed_mph >= TARGET_SPEED_MPH - ACCEL_DEADBAND_MPH:
            phase = PHASE_HOLD
        else:
            phase = PHASE_ACCEL

        # -- Throttle logic --------------------------------------------
        if phase == PHASE_ACCEL:
            powertrain.set_throttle(1.0)        # full throttle while accelerating
        else:
            powertrain.set_throttle(0.0)        # lift off near target speed

        # -- Transmission management -----------------------------------
        powertrain.auto_shift()
        powertrain.update_rpm(speed_ms)

        # -- Force calculations ----------------------------------------
        drive_force         = powertrain.compute_wheel_force()
        rolling_resistance  = powertrain.compute_rolling_resistance()
        aero_drag           = VehicleState.aero_drag_force(speed_ms)
        pb_resist_force     = park_brake.get_braking_torque() / WHEEL_RADIUS_M   # torque → force
        brake_force         = brakes.compute_brake_force(speed_mph, DT)

        net_force = drive_force - rolling_resistance - aero_drag - pb_resist_force - brake_force

        # -- Integrate -------------------------------------------------
        state.update(net_force, DT)

        # -- Logging ---------------------------------------------------
        if t >= next_log:
            print(
                f"{t:8.1f}  {state.speed_mph:10.2f}  {state.acceleration:12.4f}  "
                f"{powertrain.current_gear:5d}  {powertrain.rpm:6.0f}  "
                f"{powertrain.throttle:9.2f}  "
                f"{brake_force:10.1f}  {park_brake.get_braking_torque():12.1f}  "
                f"{phase:>18}"
            )
            next_log += LOG_INTERVAL

    # ---- Summary -----------------------------------------------------
    print()
    print("=" * 72)
    print("[SIM] Simulation complete.")
    print(f"      Final speed      : {state.speed_mph:.2f} mph")
    print(f"      Total distance   : {state.position:.1f} m  ({state.position / 1609.34:.3f} miles)")
    print(f"      Final gear       : {powertrain.current_gear}")
    print(f"      EPB torque (end) : {park_brake.get_braking_torque():.1f} Nm")
    print("=" * 72)


if __name__ == "__main__":
    run()
