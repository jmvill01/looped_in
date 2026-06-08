import unittest

from simulation.controllers.brakes import BrakesController
from simulation.controllers.park_brake import ParkBrakeController
from simulation.controllers.powertrain import PowertrainController, WHEEL_RADIUS_M
from simulation.run_simulation import ACCEL_DEADBAND_MPH, DT, DURATION, TARGET_SPEED_MPH
from simulation.vehicle import VehicleState


class SimulationSpeedHoldTests(unittest.TestCase):
    def test_simulation_reaches_target_and_applies_braking(self) -> None:
        state = VehicleState()
        park_brake = ParkBrakeController()
        powertrain = PowertrainController()
        brakes = BrakesController()
        brakes.set_target_speed(TARGET_SPEED_MPH)

        park_brake.release()
        powertrain.request_drive()

        max_speed_mph = 0.0
        max_brake_force_n = 0.0

        while state.elapsed_time <= DURATION:
            speed_mph = state.speed_mph
            speed_ms = state.speed_ms

            if speed_mph >= TARGET_SPEED_MPH - ACCEL_DEADBAND_MPH:
                powertrain.set_throttle(0.0)
            else:
                powertrain.set_throttle(1.0)

            powertrain.auto_shift()
            powertrain.update_rpm(speed_ms)

            drive_force = powertrain.compute_wheel_force()
            rolling_resistance = powertrain.compute_rolling_resistance()
            aero_drag = VehicleState.aero_drag_force(speed_ms)
            pb_resist_force = park_brake.get_braking_torque() / WHEEL_RADIUS_M
            brake_force = brakes.compute_brake_force(speed_mph, DT)
            net_force = drive_force - rolling_resistance - aero_drag - pb_resist_force - brake_force

            state.update(net_force, DT)

            max_speed_mph = max(max_speed_mph, state.speed_mph)
            max_brake_force_n = max(max_brake_force_n, brake_force)

        self.assertGreaterEqual(max_speed_mph, TARGET_SPEED_MPH)
        self.assertGreater(max_brake_force_n, 0.0)


if __name__ == "__main__":
    unittest.main()
