"""One binary reward from physical outcome; no gait or actuator commands."""

import math

from .contracts import REWARD_INPUT


class ProgressReward:
    def __init__(self, settings):
        self.settings = settings
        self.disarm()

    def disarm(self):
        self.previous = None
        self.origin = None
        self.heading = None
        self.high_water = 0.0

    @staticmethod
    def valid(simulation_time, xyz, rpy):
        return len(xyz) == len(rpy) == 3 and all(
            math.isfinite(v) for v in (simulation_time, *xyz, *rpy)
        )

    def start(self, simulation_time, xyz, rpy):
        self.disarm()
        if self.valid(simulation_time, xyz, rpy):
            self.origin = tuple(xyz)
            self.heading = (math.cos(rpy[2]), math.sin(rpy[2]))
            self.previous = (simulation_time, 0.0)

    def sample(self, simulation_time, xyz, rpy):
        if not self.valid(simulation_time, xyz, rpy):
            self.disarm()
            return dict(value=0, reason="invalid_measurement")
        if self.previous is None:
            return dict(value=0, reason="not_armed")
        dt = simulation_time - self.previous[0]
        if dt <= 0:
            self.disarm()
            return dict(value=0, reason="simulation_time_reset")
        progress = sum((xyz[i] - self.origin[i]) * self.heading[i] for i in (0, 1))
        speed = (progress - self.previous[1]) / dt
        new_progress = progress - self.high_water
        self.previous = (simulation_time, progress)
        # Update even when tilted/low: recovering old distance earns no reward.
        self.high_water = max(self.high_water, progress)
        s = self.settings
        upright = (
            abs(rpy[0]) <= s["max_abs_roll_rad"]
            and abs(rpy[1]) <= s["max_abs_pitch_rad"]
            and xyz[2] >= s["min_body_height_m"]
        )
        reason = (
            "not_upright"
            if not upright
            else "insufficient_forward_speed"
            if speed < s["min_forward_speed_m_s"]
            else "no_new_forward_progress"
            if new_progress <= s["progress_epsilon_m"]
            else "upright_forward_progress"
        )
        return dict(
            value=int(reason == "upright_forward_progress"),
            reason=reason,
            forward_progress_m=progress,
            forward_speed_m_s=speed,
            forward_high_water_m=self.high_water,
        )


class RewardPublisher:
    """Own only GAIT_REWARD_IN; command clears never touch this channel."""

    def __init__(self, publish, record=lambda event: None):
        self.publish = publish
        self.record = record
        self.value = None

    def send(self, evidence, *, native_step=None, simulation_time=None, force=False):
        value = evidence["value"]
        if type(value) is not int or value not in (0, 1):
            raise ValueError("The single reward neuron accepts binary outcomes")
        if not force and value == self.value:
            return
        response = self.publish(REWARD_INPUT, float(value))
        if not (
            isinstance(response, dict)
            and response.get("ok") is True
            and response.get("queued_for_hardware") is True
        ):
            raise RuntimeError("Reward input did not receive hardware queue acceptance")
        self.value = value
        self.record(
            dict(
                input=REWARD_INPUT,
                native_step=native_step,
                simulation_time=simulation_time,
                **evidence,
            )
        )
