import math
import types
import unittest
from robot.body_measurements import BodyMeasurements


class BodyMeasurementTests(unittest.TestCase):
    def test_raw_center_feet_and_torque_are_read_without_actuation(self):
        periods = []
        motor = types.SimpleNamespace(enableTorqueFeedback=periods.append,
                                      getTorqueFeedback=lambda: -17.2)
        foot = types.SimpleNamespace(getPosition=lambda: [1, 2, .03])
        robot = types.SimpleNamespace(getCenterOfMass=lambda: [.1, .2, .55])
        body = types.SimpleNamespace(getFromDevice=lambda device: foot)
        measurement = BodyMeasurements(body, robot, {('FL', 'HIP'): motor}, {'FL': object()}, 32)
        row = measurement.sample()
        self.assertEqual(periods, [32])
        self.assertEqual(row['center_of_mass_xyz_m'], [.1, .2, .55])
        self.assertEqual(row['foot_center_xyz_m'], {'FL': [1, 2, .03]})
        self.assertEqual(row['joint_motor_torque_nm'], {'FL_HIP': -17.2})
        self.assertEqual(row['physical_measurement_errors'], {})

    def test_unavailable_diagnostics_are_reported_without_fabricated_measurements(self):
        robot = types.SimpleNamespace(getCenterOfMass=lambda: [math.nan, 0, 0])
        body = types.SimpleNamespace(getFromDevice=lambda device: None)
        measurement = BodyMeasurements(body, robot, {('FL', 'HIP'): object()}, {'FL': object()}, 32)
        row = measurement.sample()
        self.assertIsNone(row['center_of_mass_xyz_m'])
        self.assertEqual(row['joint_motor_torque_nm'], {})
        self.assertEqual(row['foot_center_xyz_m'], {})
        self.assertEqual(set(row['physical_measurement_errors']), {'center_of_mass', 'foot:FL', 'torque:FL_HIP'})
