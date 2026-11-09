"""Read-only physical evidence. None of these measurements enters the brain."""
import math


class BodyMeasurements:
    def __init__(self, body, robot_node, motors, feet, timestep):
        self.robot = robot_node
        self.motors, self.feet, self.errors = {}, {}, {}
        for key, motor in motors.items():
            name = "_".join(key)
            try:
                motor.enableTorqueFeedback(timestep)
                self.motors[name] = motor
            except Exception as exc:
                self.errors["torque:" + name] = type(exc).__name__
        for leg, device in feet.items():
            try:
                node = body.getFromDevice(device)
                if node is None:
                    raise ValueError("Foot node unavailable")
                self.feet[leg] = node
            except Exception as exc:
                self.errors["foot:" + leg] = type(exc).__name__

    def sample(self):
        errors = dict(self.errors)

        def read(name, getter, vector=False):
            try:
                value = list(getter()) if vector else float(getter())
                values = value if vector else [value]
                if (vector and len(values) != 3) or not all(math.isfinite(v) for v in values):
                    raise ValueError("Non-finite physical measurement")
                return value
            except Exception as exc:
                errors[name] = type(exc).__name__
                return None

        return dict(
            center_of_mass_xyz_m=read("center_of_mass", self.robot.getCenterOfMass, True),
            foot_center_xyz_m={leg: read("foot:" + leg, node.getPosition, True)
                               for leg, node in self.feet.items()},
            joint_motor_torque_nm={name: read("torque:" + name, motor.getTorqueFeedback)
                                   for name, motor in self.motors.items()},
            physical_measurement_errors=errors,
        )
