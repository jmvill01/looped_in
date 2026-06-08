"""
park_brake.py — Electronic Park Brake (EPB) Controller.

Manages engagement and release of the rear-axle park brake.  When engaged the
EPB clamps a fixed holding torque onto both rear rotors; when released that
torque should drop to zero so the vehicle can move freely.
"""


class ParkBrakeController:
    """
    Electronic Park Brake controller.

    The EPB stores a resistive torque value (Nm) that is added to the rear
    wheels whenever the system is active.  Engage sets it to PARK_BRAKE_TORQUE;
    release is expected to clear it to 0.
    """

    # Maximum static holding torque applied to the rear axle (Nm)
    PARK_BRAKE_TORQUE: float = 500.0

    def __init__(self) -> None:
        self.engaged: bool = True
        self._braking_torque: float = self.PARK_BRAKE_TORQUE
        self.fault_active: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def engage(self) -> None:
        """Apply the park brake."""
        if not self.fault_active:
            self.engaged = True
            self._braking_torque = self.PARK_BRAKE_TORQUE

    def release(self) -> None:
        """
        Release the park brake.
        """
        if not self.fault_active:
            self.engaged = False
            self._braking_torque = 0.0

    def get_braking_torque(self) -> float:
        """Return the current resistive torque exerted by the park brake (Nm)."""
        return self._braking_torque

    @property
    def is_engaged(self) -> bool:
        return self.engaged
