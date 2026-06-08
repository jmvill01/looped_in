import unittest

from simulation.controllers.park_brake import ParkBrakeController


class ParkBrakeControllerTests(unittest.TestCase):
    def test_release_clears_braking_torque(self) -> None:
        controller = ParkBrakeController()

        controller.release()

        self.assertFalse(controller.is_engaged)
        self.assertEqual(controller.get_braking_torque(), 0.0)


if __name__ == "__main__":
    unittest.main()
