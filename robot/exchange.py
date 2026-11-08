"""Send one command event and observe its separate neural goal confirmation.

Transport ACK and goal acceptance are separate events. Waiting for the goal does
not block the controller's native-frame/physics loop or publish periodic inputs.
"""

import time

from .contracts import COMMAND_INPUT_SIZES, validate_channels


class CommandExchange:
    def __init__(self, publish, events, timeout, record=lambda item: None):
        self.publish = publish
        self.events = events
        self.timeout = timeout
        self.record = record
        self.sequence = 0
        self.failed = False
        self.pending = False
        self.pending_action = None
        self.ack_step = None
        self.goal_deadline = None

    def _send(self, frame):
        reply = self.publish(frame, mode="vector_f32")
        if not isinstance(reply, dict) or not all(
            reply.get(k) is True for k in ("ok", "queued_for_hardware", "atomic_frame")
        ):
            raise RuntimeError(
                "Atomic command acceptance was not confirmed; stop without retrying"
            )

    def initialize_inputs(self):
        # Clear possible retained external stimulation once at session startup.
        self._send({k: [0.0] for k in COMMAND_INPUT_SIZES})

    def command(self, action):
        if action not in ("start", "stop"):
            raise ValueError("Command must be start or stop")
        if self.failed or self.pending:
            raise RuntimeError("Command transaction is unavailable; stop and restart")
        self.pending = True
        try:
            deadline = time.monotonic() + self.timeout
            while True:
                event = self.events.wait_one(deadline)
                c = validate_channels(event)
                if (
                    c["TRANSPORT_ACK_OUT"] == 0
                    and self.events.stats()["queued_frames"] == 0
                ):
                    break
            cursor = self.events.stats()["last_received_step"]
            if self.pending_action is not None:
                self.record(
                    dict(
                        kind="command_superseded",
                        action=self.pending_action,
                        sequence=self.sequence,
                        replacement=action,
                    )
                )
            self.sequence += 1
            frame = {k: [0.0] for k in COMMAND_INPUT_SIZES}
            frame["WALK_START" if action == "start" else "WALK_STOP"] = [1.0]
            frame["TRANSPORT_ACK"] = [1.0]
            self.record(
                dict(
                    kind="command_sent",
                    action=action,
                    sequence=self.sequence,
                    after_step=cursor,
                    frame=frame,
                )
            )
            self._send(frame)
            deadline = time.monotonic() + self.timeout
            while True:
                event = self.events.wait_one(deadline)
                c = validate_channels(event)
                if event["step"] > cursor and c["TRANSPORT_ACK_OUT"] == 1:
                    break
            self.record(
                dict(
                    kind="command_ack",
                    action=action,
                    sequence=self.sequence,
                    step=event["step"],
                )
            )
            # Live inputs are one-step events. This zero event is explicit ACK
            # hygiene, not a claim that the preceding command remained asserted.
            # Request retention belongs to START_REQUEST / STOP_REQUEST in the graph.
            self._send({"TRANSPORT_ACK": [0.0]})
            self.record(dict(kind="ack_input_cleared", sequence=self.sequence))
            self.pending_action = action
            self.ack_step = event["step"]
            self.goal_deadline = time.monotonic() + self.timeout
            return event
        except Exception:
            self.failed = True
            raise
        finally:
            self.pending = False

    def observe(self, event):
        """Inspect one real frame, without waiting or choosing any motor output."""
        if self.failed:
            raise RuntimeError("Command transaction failed; stop and restart")
        if self.pending_action is None:
            return None
        try:
            c = validate_channels(event)
            if event["step"] < self.ack_step:
                return None
            action = self.pending_action
            values = dict(
                walk=c["WALK_ENABLED"],
                rest=c["REST_ACTIVE"],
                start_request=c["START_REQUEST"],
                stop_request=c["STOP_REQUEST"],
            )
            if time.monotonic() >= self.goal_deadline:
                self.record(
                    dict(
                        kind="command_timeout",
                        action=action,
                        sequence=self.sequence,
                        step=event["step"],
                        **values,
                    )
                )
                raise TimeoutError(
                    f"{action.upper()} was acknowledged, but its goal did not confirm "
                    f"within {self.timeout:g}s: WALK_ENABLED={values['walk']}, "
                    f"REST_ACTIVE={values['rest']}, "
                    f"START_REQUEST={values['start_request']}, "
                    f"STOP_REQUEST={values['stop_request']}. Inspect the command circuit."
                )
            expected = (1, 0) if action == "start" else (0, 1)
            if (values["walk"], values["rest"]) != expected:
                return None
            self._send({k: [0.0] for k in COMMAND_INPUT_SIZES})
            self.record(
                dict(
                    kind="command_confirmed",
                    action=action,
                    sequence=self.sequence,
                    step=event["step"],
                    **values,
                )
            )
            self.record(dict(kind="inputs_cleared", sequence=self.sequence))
            self.pending_action = None
            self.goal_deadline = None
            return action
        except Exception:
            self.failed = True
            raise
