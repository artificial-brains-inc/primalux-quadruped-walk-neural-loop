import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from robot.neuron_recording import NeuronRecorder, population_spikes, stream_records


def sse(kind, data, cursor=None):
    return ([f"id: {cursor}"] if cursor else []) + [
        f"event: {kind}",
        "data: " + json.dumps(data),
        "",
    ]


class NeuronRecordingTests(unittest.TestCase):
    def test_bit_order_and_inactive_neurons_are_preserved(self):
        layout = {"neurons": [f"A:{n}" for n in range(8)] + ["B:0", "C:0"]}
        raw = base64.b64encode(bytes([129, 1])).decode()
        self.assertEqual(
            population_spikes(layout, {"bits": raw}), {"A": 2, "B": 1, "C": 0}
        )
        self.assertIsNone(population_spikes(layout, None))
        with self.assertRaises(ValueError):
            population_spikes(layout, {"bits": base64.b64encode(b"a").decode()})

    def test_parser_preserves_multiline_json_and_cursor(self):
        records = list(
            stream_records(
                [
                    ": heartbeat",
                    "event: frame",
                    "id: e:1",
                    'data: {"a":',
                    "data: 1}",
                    "",
                ]
            )
        )
        self.assertEqual(records, [("frame", {"a": 1}, "e:1")])

    def trial(self, *, gap=False):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "neurons.jsonl"
            client, response = MagicMock(), MagicMock()
            client.http.stream.return_value.__enter__.return_value = response
            factory = MagicMock()
            factory.return_value.__enter__.return_value = client
            recorder = NeuronRecorder(path, "test.env", client_factory=factory)
            hello = {
                "cursor": "e:4",
                "layout": {"neurons": ["REFLEX_RL_HG:0", "REAR_LEFT_KNEE_NEG_BETA:0"]},
            }
            frame = {
                "epoch": "e",
                "sequence": 6 if gap else 5,
                "item": {"step": 50},
                "telemetry": {"bits": "AQ=="},
            }

            def lines():
                yield from sse("hello", hello)
                yield from sse("frame", frame, "e:5")
                recorder.closed.set()

            response.iter_lines.side_effect = lines
            recorder._run()
            client.http.stream.assert_called_once()
            self.assertEqual(
                client.http.stream.call_args.args, ("GET", "/api/brain/stream")
            )
            self.assertEqual(
                client.http.stream.call_args.kwargs["params"], {"telemetry": 1}
            )
            return [json.loads(x) for x in path.read_text().splitlines()]

    def test_records_actual_firing_without_turning_diagnostics_into_inputs(self):
        records = self.trial()
        self.assertEqual([r["event"] for r in records], ["hello", "frame"])
        self.assertEqual(records[1]["native_step"], 50)
        self.assertEqual(
            records[1]["spike_counts"],
            {"REFLEX_RL_HG": 1, "REAR_LEFT_KNEE_NEG_BETA": 0},
        )
        self.assertEqual(records[1]["data"]["telemetry"]["bits"], "AQ==")

    def test_sequence_gap_is_an_explicit_recording_error(self):
        records = self.trial(gap=True)
        self.assertEqual([r["event"] for r in records], ["hello", "recorder_error"])
        self.assertEqual(records[-1]["error_type"], "ValueError")
