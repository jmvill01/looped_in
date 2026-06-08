"""
brakes.py — Hydraulic Brakes Controller.

Implements a Proportional-Integral (PI) closed-loop controller that commands
hydraulic brake force to regulate vehicle speed at a set target.  The
controller activates once the vehicle has reached the desired cruise speed and
applies corrective braking whenever the vehicle exceeds that setpoint.

Units
-----
  - Speed : mph  (matches the driver-facing setpoint interface)
  - Force : N    (output delivered to vehicle physics model)
"""


# Maximum total hydraulic brake force available (N)
MAX_BRAKE_FORCE_N: float = 8000.0


class BrakesController:
    """
    PI speed-regulation controller using hydraulic braking.

    When active, the controller computes a brake-force demand each timestep
    to hold the vehicle at ``target_speed_mph``.  Braking force is always
    non-negative (the controller cannot accelerate the vehicle).
    """

    def __init__(self) -> None:
        self.target_speed_mph: float = 0.0
        self.active: bool = False

        # PI gains — tuned for a 1 361 kg vehicle
        self.Kp: float = 150.0   # N per mph of speed error
        self.Ki: float = 5.0     # N per (mph · s) of integrated error

        self._integral: float = 0.0

    # ------------------------------------------------------------------
    # Setpoint management
    # ------------------------------------------------------------------

    def set_target_speed(self, speed_mph: float) -> None:
        """Activate the brake controller and set the target hold speed."""
        self.target_speed_mph = speed_mph
        self.active = True
        self._integral = 0.0

    def deactivate(self) -> None:
        """Turn off brake control (e.g. when driver requests full acceleration)."""
        self.active = False
        self._integral = 0.0

    # ------------------------------------------------------------------
    # Brake force computation
    # ------------------------------------------------------------------

    def compute_brake_force(self, current_speed_mph: float, dt: float) -> float:
        """
        Compute the hydraulic brake force (N) needed to maintain target speed.

        Returns a value in ``[0, MAX_BRAKE_FORCE_N]``; zero means no braking.

        Positive speed error means the vehicle is above target and should brake:

        .. code-block:: python

            error = current_speed_mph - self.target_speed_mph
        """
        if not self.active:
            return 0.0

        error = current_speed_mph - self.target_speed_mph

        self._integral += error * dt
        # Clamp integrator to prevent unbounded wind-up
        self._integral = max(-200.0, min(200.0, self._integral))

        force = self.Kp * error + self.Ki * self._integral

        return max(0.0, min(MAX_BRAKE_FORCE_N, force))

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset integrator and deactivate."""
        self._integral = 0.0
        self.active = False
