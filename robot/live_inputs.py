"""Publish current observations without blocking Webots or pacing the brain."""

import copy
import threading
import time
from collections import deque

from .contracts import LEGS, REWARD_INPUT, REWARD_INPUT_NEURONS, TILT_INPUTS, TILT_NEURONS
from .contact import encode_contacts
from .reflex import encode_tilt


class Receipt:
    """HTTP queue acceptance, not a neural ACK or completed movement."""

    def __init__(self):
        self.ready = threading.Event()
        self.after_step = None
        self.accepted_at = None
        self.error = None


class LiveInputs:
    def __init__(self, publish, cursor, settings, *, tilt_record=lambda e: None,
                 reward_record=lambda e: None, contact_record=lambda e: None):
        self.publish, self.cursor, self.settings = publish, cursor, settings
        self.tilt_record, self.reward_record = tilt_record, reward_record
        self.contact_record = contact_record
        self.condition = threading.Condition()
        self.commands = deque()
        self.latest = None
        self.closing = False
        self.failure = None
        self.thread = None
        self.in_flight = False
        self.replaced = 0
        self.published = 0
        self.last_zero = False

    def __enter__(self):
        self.thread = threading.Thread(target=self._run, name="spot-live-inputs")
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.close()
        self.check_health()

    def check_health(self):
        with self.condition:
            if self.failure is not None:
                raise RuntimeError(f"Live input publication failed: {self.failure}")

    def command(self, payload):
        receipt = Receipt()
        with self.condition:
            self.check_health()
            if self.closing:
                raise RuntimeError("Input sender is closed")
            # Do not deliver a pre-command reward/tilt capture after this event.
            if self.latest is not None:
                self.replaced += 1
                self.latest = None
            self.commands.append((copy.deepcopy(payload), receipt))
            self.condition.notify()
        return receipt

    def feedback(self, rpy, evidence, *, suspended=False, native_step=None,
                 simulation_time=None, contacts=None, tilt_suspended=False):
        value = evidence["value"]
        if type(value) is not int or value not in (0, 1):
            raise ValueError("The reward population accepts binary outcome magnitudes")
        tilt = (encode_tilt(rpy, self.settings)
                if self.settings["enabled"] and not (suspended or tilt_suspended)
                else {name: [0] * TILT_NEURONS for name in TILT_INPUTS})
        if contacts is None:
            if not suspended:
                raise ValueError("Live feedback requires measured foot contacts")
            contacts = dict.fromkeys(LEGS, 0)
        contact_inputs = encode_contacts(contacts, suspended=suspended)
        capture = dict(inputs={**tilt, **contact_inputs}, tilt_inputs=tilt,
                       contact_inputs=contact_inputs, measured_contacts=dict(contacts),
                       measured_rpy_rad=list(rpy), evidence=dict(evidence),
                       tilt_suspended=suspended or tilt_suspended,
                       suspended=suspended, native_step=native_step,
                       simulation_time=simulation_time, captured_at=time.monotonic())
        with self.condition:
            self.check_health()
            if self.closing:
                raise RuntimeError("Input sender is closed")
            if self.latest is not None:
                self.replaced += 1
            self.latest = capture
            self.condition.notify()
        return tilt

    def stats(self):
        with self.condition:
            return dict(pending_feedback=int(self.latest is not None),
                        pending_commands=len(self.commands), in_flight=self.in_flight,
                        replaced_unsent_feedback=self.replaced,
                        published_feedback=self.published)

    def _send(self, payload):
        result = self.publish(payload, mode="vector_f32")
        if not isinstance(result, dict) or not all(
            result.get(k) is True for k in ("ok", "queued_for_hardware", "atomic_frame")
        ):
            raise RuntimeError("Atomic live input queue acceptance was not confirmed")

    def _deliver(self, command=None, capture=None):
        if command is not None:
            payload, receipt = command
            try:
                self._send(payload)
                receipt.after_step = self.cursor()
                receipt.accepted_at = time.monotonic()
            except Exception as exc:
                receipt.error = str(exc)
                raise
            finally:
                receipt.ready.set()
            return
        value = capture["evidence"]["value"]
        zero = value == 0 and not any(v[0] for v in capture["inputs"].values())
        if zero and self.last_zero:
            return
        reward_class = "positive_outcome" if value else "no_reward"
        # All observations belong to the same completed physics step. The
        # public SDK encodes reward_population within this atomic sensor frame.
        payload = dict(capture["inputs"])
        payload[REWARD_INPUT] = dict(signal=float(value), mode="reward_population",
                                     meta={"reward_class": reward_class})
        started = time.monotonic()
        self._send(payload)
        common = dict(native_step=capture["native_step"],
                      simulation_time=capture["simulation_time"],
                      capture_age_at_send_seconds=started - capture["captured_at"],
                      publish_wall_seconds=time.monotonic() - started)
        self.tilt_record(dict(**common, inputs=capture["tilt_inputs"],
                              measured_rpy_rad=capture["measured_rpy_rad"],
                              suspended=capture["tilt_suspended"]))
        self.contact_record(dict(**common, inputs=capture["contact_inputs"],
                                 measured_contacts=capture["measured_contacts"],
                                 suspended=capture["suspended"]))
        self.reward_record(dict(**common, input=REWARD_INPUT, reward_class=reward_class,
                                input_population_neurons=REWARD_INPUT_NEURONS,
                                active_input_neurons=value * REWARD_INPUT_NEURONS,
                                **capture["evidence"]))
        self.last_zero = zero
        with self.condition:
            self.published += 1

    def _run(self):
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(
                        lambda: self.closing or self.commands or self.latest is not None)
                    if self.closing:
                        return
                    command = self.commands.popleft() if self.commands else None
                    capture = None
                    if command is None:
                        capture, self.latest = self.latest, None
                    self.in_flight = True
                try:
                    self._deliver(command, capture)
                finally:
                    with self.condition:
                        self.in_flight = False
        except Exception as exc:
            with self.condition:
                self.failure = str(exc)
                self.condition.notify_all()

    def close(self):
        with self.condition:
            self.closing = True
            self.latest = None
            self.commands.clear()
            self.condition.notify_all()
        if self.thread is not None:
            # SDK HTTP calls have their own timeout. Join before closing logs
            # or Stop/save, so an in-flight capture cannot arrive after shutdown.
            self.thread.join()
