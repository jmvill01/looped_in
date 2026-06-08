import unittest

from simulation.controllers.brakes import BrakesController


class BrakesControllerTests(unittest.TestCase):
    def test_overspeed_produces_positive_brake_demand(self) -> None:
        controller = BrakesController()
        controller.set_target_speed(30.0)

        demand_n = controller.compute_brake_force(current_speed_mph=34.0, dt=0.1)

        self.assertGreater(demand_n, 0.0)

    def test_below_target_speed_produces_zero_brake_demand(self) -> None:
        controller = BrakesController()
        controller.set_target_speed(30.0)

        demand_n = controller.compute_brake_force(current_speed_mph=29.0, dt=0.1)

        self.assertEqual(demand_n, 0.0)


if __name__ == "__main__":
    unittest.main()
