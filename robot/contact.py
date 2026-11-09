"""Encode foot-pad bumper measurements; all gait decisions remain neural."""

import math

from .contracts import CONTACT_DEVICE_NAMES, CONTACT_INPUTS, AIR_INPUTS, CONTACT_NEURONS, LEGS


def setup_contact_sensors(body, timestep):
    sensors = {}
    for leg, name in CONTACT_DEVICE_NAMES.items():
        sensor = body.getDevice(name)
        if sensor is None:
            raise RuntimeError(f"Missing foot TouchSensor: {name}. Open the bundled world.")
        if sensor.getType() != sensor.BUMPER:
            raise RuntimeError(f"Foot TouchSensor must be a bumper: {name}")
        sensor.enable(timestep)
        sensors[leg] = sensor
    return sensors


def encode_contacts(values, *, suspended=False):
    if set(values) != set(LEGS):
        raise ValueError("Foot contact requires measurements for FL, FR, RL and RR")
    for value in values.values():
        if type(value) not in (int, float) or not math.isfinite(value) or value not in (0, 1):
            raise ValueError("Foot bumper measurements must be finite zero or one")
    encoded = {}
    for leg in LEGS:
        # Both rails are measured evidence. No phase, edge detection or gait
        # history lives in Python; AIR_SEEN memory is in the neural graph.
        encoded[CONTACT_INPUTS[leg]] = [0 if suspended else int(values[leg])] * CONTACT_NEURONS
        encoded[AIR_INPUTS[leg]] = [0 if suspended else 1 - int(values[leg])] * CONTACT_NEURONS
    return encoded


def clear_contacts(publish):
    result = publish(encode_contacts(dict.fromkeys(LEGS, 0), suspended=True), mode="vector_f32")
    if not isinstance(result, dict) or not all(
        result.get(k) is True for k in ("ok", "queued_for_hardware", "atomic_frame")
    ):
        raise RuntimeError("Foot-contact clear did not receive atomic queue acceptance")
