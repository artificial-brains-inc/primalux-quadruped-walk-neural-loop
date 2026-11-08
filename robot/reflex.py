"""Digitize physical IMU readings; leg choice and burst lifetime stay neural."""

import math
import time

from .contracts import TILT_INPUTS, TILT_NEURONS


def encode_tilt(rpy, settings):
    if len(rpy) != 3 or not all(math.isfinite(v) for v in rpy):
        raise ValueError("Reflex input requires a finite IMU orientation")
    threshold = settings["tilt_threshold_rad"]
    roll, pitch = rpy[:2]
    return dict(
        zip(
            TILT_INPUTS,
            (
                [int(roll <= -threshold)] * TILT_NEURONS,
                [int(roll >= threshold)] * TILT_NEURONS,
                [int(pitch <= -threshold)] * TILT_NEURONS,
                [int(pitch >= threshold)] * TILT_NEURONS,
            ),
            strict=True,
        )
    )


class TiltPublisher:
    def __init__(self, publish, settings, record=lambda event: None):
        self.publish, self.settings, self.record = publish, settings, record
        self.previous = None

    def send(
        self,
        rpy,
        *,
        suspended=False,
        native_step=None,
        simulation_time=None,
        force=False,
    ):
        # Suspension is for the explicit simulator recovery/rhythm test only.
        # Ordinary WALK/REST gating is neural; no leg or gait state is read here.
        active = self.settings["enabled"] and not suspended
        payload = (
            encode_tilt(rpy, self.settings)
            if active
            else {name: [0] * TILT_NEURONS for name in TILT_INPUTS}
        )
        nonzero = any(v[0] for v in payload.values())
        if not force and not nonzero and payload == self.previous:
            return payload
        started = time.monotonic()
        response = self.publish(payload)
        if not (
            isinstance(response, dict)
            and response.get("ok") is True
            and response.get("queued_for_hardware") is True
            and response.get("atomic_frame") is True
        ):
            raise RuntimeError(
                "Tilt inputs did not receive atomic hardware queue acceptance"
            )
        self.previous = payload
        self.record(
            dict(
                native_step=native_step,
                simulation_time=simulation_time,
                measured_rpy_rad=list(rpy),
                inputs=payload,
                suspended=suspended,
                publish_wall_seconds=time.monotonic() - started,
            )
        )
        return payload
