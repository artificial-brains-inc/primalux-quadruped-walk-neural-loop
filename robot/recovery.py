"""Simulator assistance, separate from neural gait and learned self-righting."""

import math


class Recovery:
    def __init__(self, settings, upright):
        self.settings = settings
        self.upright = upright
        self.state = "idle"
        self.resume = False
        self.count = 0
        self.fallen_since = None
        self.stable_since = None
        self.cooldown_until = 0.0
        self.started = 0.0
        self.reason = None

    @property
    def active(self):
        return self.state != "idle"

    @staticmethod
    def valid(xyz, rpy):
        return len(xyz) == len(rpy) == 3 and all(math.isfinite(v) for v in (*xyz, *rpy))

    def detect_fall(self, now, xyz, rpy):
        if (
            self.active
            or not self.settings["automatic"]
            or now < self.cooldown_until
            or not self.valid(xyz, rpy)
        ):
            self.fallen_since = None
            return False
        tilt = math.acos(max(-1.0, min(1.0, math.cos(rpy[0]) * math.cos(rpy[1]))))
        fallen = (
            tilt >= self.settings["fall_tilt_rad"]
            or xyz[2] < self.settings["fall_height_m"]
        )
        if not fallen:
            self.fallen_since = None
        elif self.fallen_since is None:
            self.fallen_since = now
        return (
            self.fallen_since is not None
            and now - self.fallen_since >= self.settings["fall_delay_seconds"]
        )

    def begin(self, now, *, resume, reason):
        if self.active:
            return False
        self.state = "waiting_stop"
        self.resume = resume
        self.reason = reason
        self.started = now
        self.fallen_since = self.stable_since = None
        return True

    def update(self, now, *, stopped, xyz, rpy):
        if self.state == "waiting_stop":
            if stopped:
                self.state = "settling"
                self.started = now
                self.count += 1
                return "restore"
            if now - self.started > self.settings["stop_timeout_seconds"]:
                raise TimeoutError(
                    "Recovery: REST or quiet motor outputs did not confirm"
                )
        elif self.state == "settling":
            upright = (
                self.valid(xyz, rpy)
                and xyz[2] >= self.upright["min_body_height_m"]
                and abs(rpy[0]) <= self.upright["max_abs_roll_rad"]
                and abs(rpy[1]) <= self.upright["max_abs_pitch_rad"]
            )
            if not stopped or not upright:
                self.stable_since = None
            elif self.stable_since is None:
                self.stable_since = now
            if (
                self.stable_since is not None
                and now - self.stable_since >= self.settings["settle_seconds"]
            ):
                self.state = "idle"
                self.cooldown_until = now + self.settings["cooldown_seconds"]
                return "ready"
            if now - self.started > self.settings["settle_timeout_seconds"]:
                raise TimeoutError(
                    "Recovery: Spot did not settle upright; stopping session"
                )
        return None
