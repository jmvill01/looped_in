"""
powertrain.py — Powertrain Controller.

Models engine torque production, a 6-speed automatic transmission with
auto-shift logic, and the conversion of engine torque to linear drive force
at the rear wheels.

Units
-----
  - Torque   : Nm
  - Force    : N
  - Speed    : m/s  (internal); mph exposed by VehicleState
  - Distance : m
  - Angles   : radians
"""

import math


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

WHEEL_RADIUS_M: float = 0.33        # Effective rolling radius (m) — ~225/55R17
AXLE_RATIO: float = 3.73            # Rear differential ratio

IDLE_RPM: float = 800.0
REDLINE_RPM: float = 7000.0

# 6-speed automatic transmission gear ratios (low → overdrive)
GEAR_RATIOS: list[float] = [3.82, 2.36, 1.69, 1.31, 1.00, 0.79]

# Peak engine torque of a naturally-aspirated 2.5 L petrol engine (Nm)
PEAK_TORQUE_NM: float = 350.0

# Vehicle mass — used for rolling resistance force calculation
VEHICLE_MASS_KG: float = 1361.0
GRAVITY: float = 9.81

# Rolling resistance coefficient (dimensionless)
# Typical value for a passenger car on tarmac: 0.010 – 0.015
# Correct rolling-resistance coefficient for a passenger car on tarmac.
ROLLING_RESISTANCE_COEFF: float = 0.013

# Shift thresholds (RPM)
UPSHIFT_RPM: float = 6000.0     # Correct upshift threshold
DOWNSHIFT_RPM: float = 2000.0   # Correct downshift threshold


# ---------------------------------------------------------------------------
# PowertrainController
# ---------------------------------------------------------------------------

class PowertrainController:
    """
    Manages engine torque, automatic gear selection, and drive-force delivery.
    """

    def __init__(self) -> None:
        self.throttle: float = 0.0          # Normalised pedal position [0, 1]
        self.current_gear: int = 1
        self.rpm: float = IDLE_RPM
        self.drive_active: bool = False     # Drive range selected?

    # ------------------------------------------------------------------
    # Engine model
    # ------------------------------------------------------------------

    def _engine_torque_nm(self) -> float:
        """
        Piecewise engine torque curve (Nm) as a function of current RPM.

        Torque rises linearly from 30 % at 1 000 RPM to peak at 4 000 RPM,
        then falls linearly to zero at redline (7 000 RPM).
        """
        rpm = self.rpm
        if rpm < 1000.0:
            return PEAK_TORQUE_NM * 0.30
        if rpm < 4000.0:
            return PEAK_TORQUE_NM * (0.30 + 0.70 * (rpm - 1000.0) / 3000.0)
        # Decline above peak power
        return PEAK_TORQUE_NM * max(0.0, 1.0 - (rpm - 4000.0) / (REDLINE_RPM - 4000.0))

    # ------------------------------------------------------------------
    # Wheel-force & resistances
    # ------------------------------------------------------------------

    def compute_wheel_force(self) -> float:
        """
        Return drive force delivered at the tyre contact patch (N).

        F = (T_engine × throttle × G_gear × G_axle) / R_wheel
        """
        if not self.drive_active:
            return 0.0
        engine_torque = self._engine_torque_nm() * self.throttle
        gear_ratio = GEAR_RATIOS[self.current_gear - 1]
        wheel_torque = engine_torque * gear_ratio * AXLE_RATIO
        return wheel_torque / WHEEL_RADIUS_M

    def compute_rolling_resistance(self) -> float:
        """
        Return tyre rolling resistance force (N).

        F_rr = Crr × m × g

        With the calibrated coefficient (0.013), this evaluates to
        ≈ 174 N for the default vehicle parameters.
        """
        return ROLLING_RESISTANCE_COEFF * VEHICLE_MASS_KG * GRAVITY

    # ------------------------------------------------------------------
    # Transmission
    # ------------------------------------------------------------------

    def auto_shift(self) -> None:
        """
        Automatic gear-shift logic — called once per simulation timestep.

        The transmission should:
          • Upshift   when RPM rises above UPSHIFT_RPM  (6 000 RPM).
          • Downshift when RPM falls below DOWNSHIFT_RPM (2 000 RPM).

        .. warning:: **BUG-2** — The upshift condition uses the wrong comparison
           operator.  ``self.rpm < UPSHIFT_RPM`` fires immediately from idle
           (800 RPM), causing the transmission to ratchet straight to 6th gear
           within the first few timesteps.  At 6th gear the drive torque is too
           low to accelerate the vehicle from a standstill, producing very
           sluggish launch behaviour.
        """
        # CORRECT:   if self.rpm > UPSHIFT_RPM and self.current_gear < len(GEAR_RATIOS):
        # BUG-2:     operator is inverted (<  instead of >) so the condition fires
        #            whenever rpm is *below* UPSHIFT_RPM — i.e. always at idle
        if self.rpm < UPSHIFT_RPM and self.current_gear < len(GEAR_RATIOS):  # BUG-2
            self.current_gear += 1
        elif self.rpm < DOWNSHIFT_RPM and self.current_gear > 1:
            self.current_gear -= 1

    # ------------------------------------------------------------------
    # RPM estimation
    # ------------------------------------------------------------------

    def update_rpm(self, vehicle_speed_ms: float) -> None:
        """Estimate engine RPM from vehicle speed, gear ratio, and axle ratio."""
        gear_ratio = GEAR_RATIOS[self.current_gear - 1]
        wheel_rpm = (vehicle_speed_ms / WHEEL_RADIUS_M) * (60.0 / (2.0 * math.pi))
        self.rpm = max(IDLE_RPM, wheel_rpm * gear_ratio * AXLE_RATIO)

    # ------------------------------------------------------------------
    # Throttle management
    # ------------------------------------------------------------------

    def set_throttle(self, value: float) -> None:
        """Set normalised throttle position, clamped to [0, 1]."""
        self.throttle = max(0.0, min(1.0, value))

    def release_throttle(self) -> None:
        self.throttle = 0.0

    def request_drive(self) -> None:
        """Select Drive range (D) — enables torque delivery."""
        self.drive_active = True
