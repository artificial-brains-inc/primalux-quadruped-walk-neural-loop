"""Read-only recording of the device stream used by the SDK neuron viewer.

This observer never publishes inputs, selects actions or paces body/brain steps.
Raw neuron bitsets and their layout are retained, including inactive neurons.
"""

import base64
import json
import threading
from collections import Counter

import httpx


def stream_records(lines):
    kind, payload, cursor = "message", [], None
    for line in lines:
        if not line:
            if payload:
                yield kind, json.loads("\n".join(payload)), cursor
            kind, payload, cursor = "message", [], None
        elif line.startswith("event:"):
            kind = line[6:].strip()
        elif line.startswith("data:"):
            payload.append(line[5:].lstrip())
        elif line.startswith("id:"):
            cursor = line[3:].strip()


def population_spikes(layout, telemetry):
    if not telemetry or "bits" not in telemetry:
        return None
    names = layout["neurons"]
    bits = base64.b64decode(telemetry["bits"], validate=True)
    if len(bits) != (len(names) + 7) // 8:
        raise ValueError("Neuron telemetry width does not match its layout")
    counts = Counter({name.rsplit(":", 1)[0]: 0 for name in names})
    for index, name in enumerate(names):
        counts[name.rsplit(":", 1)[0]] += (bits[index // 8] >> (index % 8)) & 1
    return dict(counts)


class NeuronRecorder:
    def __init__(self, path, env_path, *, client_factory=None):
        self.path, self.env_path = path, env_path
        self.client_factory = client_factory
        self.closed = threading.Event()
        self.response = None
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.closed.set()
        if self.response is not None:
            try:
                self.response.close()
            except Exception:
                pass
        if self.thread is not None:
            self.thread.join(timeout=1)

    def _run(self):
        from ab_sdk.primalux import PrimaLuxClient

        factory = self.client_factory or PrimaLuxClient.from_env
        try:
            with self.path.open("x", buffering=1) as log:
                try:
                    with factory(self.env_path) as client:
                        with client.http.stream(
                            "GET",
                            "/api/brain/stream",
                            params={"telemetry": 1},
                            timeout=httpx.Timeout(10, connect=5),
                        ) as response:
                            self.response = response
                            response.raise_for_status()
                            layout, epoch, sequence = None, None, None
                            for kind, data, cursor in stream_records(
                                response.iter_lines()
                            ):
                                if self.closed.is_set():
                                    break
                                record = {"event": kind, "cursor": cursor, "data": data}
                                if kind == "hello":
                                    layout = data["layout"]
                                    epoch, seq = data["cursor"].rsplit(":", 1)
                                    sequence = int(seq)
                                    if data.get("error"):
                                        raise ValueError(
                                            "Device neuron observation unavailable"
                                        )
                                    print(
                                        f"[SPOT] Recording {len(layout['neurons'])} neurons to {self.path.name}",
                                        flush=True,
                                    )
                                elif kind == "frame":
                                    if (
                                        layout is None
                                        or data["epoch"] != epoch
                                        or data["sequence"] != sequence + 1
                                    ):
                                        raise ValueError(
                                            "Neuron recording sequence gap or changed run"
                                        )
                                    sequence = data["sequence"]
                                    record["native_step"] = data["item"]["step"]
                                    record["spike_counts"] = population_spikes(
                                        layout, data.get("telemetry")
                                    )
                                log.write(json.dumps(record) + "\n")
                                if kind in ("error", "gap", "reset"):
                                    raise ValueError("Device ended neuron observation")
                            if not self.closed.is_set():
                                raise EOFError("Neuron observation stream ended")
                except Exception as exc:
                    if not self.closed.is_set():
                        log.write(
                            json.dumps(
                                {
                                    "event": "recorder_error",
                                    "error_type": type(exc).__name__,
                                }
                            )
                            + "\n"
                        )
                        print(
                            f"[SPOT] Neuron recording stopped: {type(exc).__name__}. Motor control continues.",
                            flush=True,
                        )
        except Exception as exc:
            print(
                f"[SPOT] Cannot write neuron recording: {type(exc).__name__}",
                flush=True,
            )
        finally:
            self.response = None
