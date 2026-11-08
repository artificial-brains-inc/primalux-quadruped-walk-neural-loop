"""One START/STOP event; observe goal readouts without a neural ACK handshake."""

import time

from .contracts import COMMAND_INPUT_SIZES, validate_channels


class CommandExchange:
    def __init__(self, submit, timeout, record=lambda item: None):
        self.submit, self.timeout, self.record = submit, timeout, record
        self.sequence = 0
        self.failed = False
        self.pending_action = None
        self.receipt = None
        self.reported_acceptance = False

    def initialize_inputs(self):
        # Preserve the installed design. Its isolated legacy ACK input is
        # cleared here and never stimulated or read by this adapter.
        self.submit({k: [0.0] for k in COMMAND_INPUT_SIZES})

    def command(self, action):
        if action not in ("start", "stop"):
            raise ValueError("Command must be start or stop")
        if self.failed:
            raise RuntimeError("Command transaction failed; stop and restart")
        if self.pending_action is not None:
            self.record(dict(kind="command_superseded", action=self.pending_action,
                             sequence=self.sequence, replacement=action))
        self.sequence += 1
        frame = dict(WALK_START=[float(action == "start")],
                     WALK_STOP=[float(action == "stop")])
        self.receipt = self.submit(frame)
        self.pending_action = action
        self.reported_acceptance = False
        self.record(dict(kind="command_queued", action=action, sequence=self.sequence,
                         frame=frame))

    def observe(self, event):
        if self.failed:
            raise RuntimeError("Command transaction failed; stop and restart")
        if self.pending_action is None or not self.receipt.ready.is_set():
            return None
        try:
            if self.receipt.error:
                raise RuntimeError(self.receipt.error)
            if not self.reported_acceptance:
                self.record(dict(kind="command_sent", action=self.pending_action,
                                 sequence=self.sequence, after_step=self.receipt.after_step))
                self.reported_acceptance = True
            c = validate_channels(event)
            values = dict(walk=c["WALK_ENABLED"], rest=c["REST_ACTIVE"],
                          start_request=c["START_REQUEST"], stop_request=c["STOP_REQUEST"])
            if time.monotonic() - self.receipt.accepted_at >= self.timeout:
                self.record(dict(kind="command_timeout", action=self.pending_action,
                                 sequence=self.sequence, step=event["step"], **values))
                raise TimeoutError(
                    f"{self.pending_action.upper()} did not confirm within {self.timeout:g}s: "
                    f"WALK_ENABLED={values['walk']}, REST_ACTIVE={values['rest']}, "
                    f"START_REQUEST={values['start_request']}, STOP_REQUEST={values['stop_request']}.")
            if self.receipt.after_step is not None and event["step"] <= self.receipt.after_step:
                return None
            expected = (1, 0) if self.pending_action == "start" else (0, 1)
            if (values["walk"], values["rest"]) != expected:
                return None
            action = self.pending_action
            self.record(dict(kind="command_confirmed", action=action,
                             sequence=self.sequence, step=event["step"], **values))
            self.pending_action = None
            return action
        except Exception:
            self.failed = True
            raise
