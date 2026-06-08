"""
vehicle.py — Vehicle physics model.

Represents a ~3 000 lb (1 361 kg) front-engine, rear-wheel-drive passenger car.
All internal quantities use SI units (m, s, N, kg).  Speed is exposed in both
m/s and mph for convenience.
"""

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

MASS_KG: float = 1361.0          # Vehicle kerb mass (kg)  ≈ 3 000 lb
GRAVITY: float = 9.81            # Gravitational acceleration (m/s²)

# Aerodynamic parameters
FRONTAL_AREA_M2: float = 2.2     # Frontal area (m²)
DRAG_COEFFICIENT: float = 0.30   # Cd — typical mid-size sedan
AIR_DENSITY: float = 1.225       # ρ (kg/m³) at sea level, 15 °C


# ---------------------------------------------------------------------------
# VehicleState
# ---------------------------------------------------------------------------

class VehicleState:
    """Mutable snapshot of vehicle kinematic state."""

    def __init__(self) -> None:
        self.speed_ms: float = 0.0        # longitudinal speed (m/s)
        self.speed_mph: float = 0.0       # same, in mph
        self.acceleration: float = 0.0   # longitudinal acceleration (m/s²)
        self.position: float = 0.0       # distance travelled (m)
        self.elapsed_time: float = 0.0   # simulation clock (s)

    # ------------------------------------------------------------------
    # Integration step
    # ------------------------------------------------------------------

    def update(self, net_force_n: float, dt: float) -> None:
        """
        Advance state by one timestep *dt* (s) given net longitudinal force.

        Uses Euler forward integration.  Speed is clamped to >= 0 so the
        vehicle cannot roll backwards in this simplified model.
        """
        self.acceleration = net_force_n / MASS_KG
        self.speed_ms = max(0.0, self.speed_ms + self.acceleration * dt)
        self.speed_mph = self.speed_ms * 2.23694
        self.position += self.speed_ms * dt
        self.elapsed_time += dt

    # ------------------------------------------------------------------
    # Aerodynamic drag helper (static — depends only on speed)
    # ------------------------------------------------------------------

    @staticmethod
    def aero_drag_force(speed_ms: float) -> float:
        """Return aerodynamic drag force (N) at the given speed (m/s)."""
        return 0.5 * AIR_DENSITY * DRAG_COEFFICIENT * FRONTAL_AREA_M2 * speed_ms ** 2
