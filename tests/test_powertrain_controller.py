import unittest

from simulation.controllers.powertrain import (
    GRAVITY,
    ROLLING_RESISTANCE_COEFF,
    VEHICLE_MASS_KG,
    PowertrainController,
)


class PowertrainControllerTests(unittest.TestCase):
    def test_rolling_resistance_matches_physical_expectation(self) -> None:
        controller = PowertrainController()

        expected_force_n = ROLLING_RESISTANCE_COEFF * VEHICLE_MASS_KG * GRAVITY

        self.assertAlmostEqual(controller.compute_rolling_resistance(), expected_force_n, places=6)
        self.assertLess(controller.compute_rolling_resistance(), 500.0)

    def test_launch_drive_force_exceeds_rolling_resistance(self) -> None:
        controller = PowertrainController()
        controller.request_drive()
        controller.set_throttle(1.0)

        self.assertGreater(controller.compute_wheel_force(), controller.compute_rolling_resistance())


if __name__ == "__main__":
    unittest.main()
