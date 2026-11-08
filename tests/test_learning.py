import math
import unittest

from design_brain import create_brain
from robot.configuration import load_config
from robot.contracts import REWARD_INPUT
from robot.reward import ProgressReward, RewardPublisher


class LearningGraphTests(unittest.TestCase):
    def test_only_local_release_recovery_paths_are_plastic(self):
        d = create_brain().to_dict()
        plastic = [e for e in d["connections"] if e.get("rule") == "STDP3"]
        expected = {
            (f"PHASE_{p}_RELEASE", f"PHASE_{p}_{target}")
            for p in ("A", "B")
            for target in ("FEEDBACK_BETA", "BETA")
        }
        self.assertEqual({(e["from"], e["to"]) for e in plastic}, expected)
        for edge in plastic:
            self.assertEqual(edge["type"], "inh")
            self.assertEqual(edge["reward"], "GAIT_REWARD")
            self.assertEqual(edge["reward_type"], "LTP")
            self.assertEqual(edge["role"], "feedback")
            self.assertEqual(edge["strength"], 4)
        for edge in d["connections"]:
            if (edge["from"], edge["to"]) not in expected:
                self.assertNotIn("rule", edge)

    def test_reward_does_not_choose_a_phase_or_drive_a_motor(self):
        d = create_brain().to_dict()
        self.assertEqual(
            next(n for n in d["nodes"] if n["name"] == "GAIT_REWARD")["rhythm"],
            "dopaminergic",
        )
        edges = [
            (e["from"], e["to"])
            for e in d["connections"]
            if e["from"].startswith("GAIT_REWARD")
        ]
        self.assertEqual(
            edges,
            [(REWARD_INPUT, "GAIT_REWARD_RELAY"), ("GAIT_REWARD_RELAY", "GAIT_REWARD")],
        )

    def test_static_comparison_changes_only_learning_metadata_and_name(self):
        learning, static = (
            create_brain().to_dict(),
            create_brain(learning=False).to_dict(),
        )
        self.assertEqual(learning["nodes"], static["nodes"])
        for a, b in zip(learning["connections"], static["connections"], strict=True):
            self.assertEqual(
                {
                    k: v
                    for k, v in a.items()
                    if k not in ("rule", "reward", "reward_type")
                },
                b,
            )


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.reward = ProgressReward(load_config()["reward"])
        self.reward.start(0, [0, 0, 0.624], [0, 0, 0])

    def sample(self, t, x=0, y=0, z=0.624, roll=0, pitch=0):
        return self.reward.sample(t, [x, y, z], [roll, pitch, 0])

    def test_only_new_upright_forward_progress_is_rewarded(self):
        self.assertEqual(self.sample(0.032, x=0.002)["value"], 1)
        self.assertEqual(self.sample(0.064, x=0.002)["value"], 0)
        self.assertEqual(self.sample(0.096, x=0.001)["value"], 0)
        self.assertEqual(self.sample(0.128, x=0.002)["value"], 0)
        self.assertEqual(self.sample(0.160, x=0.004)["value"], 1)

    def test_lateral_motion_does_not_count(self):
        self.assertEqual(self.sample(0.032, y=0.1)["value"], 0)

    def test_low_or_tilted_body_receives_no_reward(self):
        for kwargs in (dict(z=0.2), dict(roll=0.8), dict(pitch=-0.8)):
            self.reward.start(0, [0, 0, 0.624], [0, 0, 0])
            self.assertEqual(self.sample(0.032, x=0.002, **kwargs)["value"], 0)

    def test_heading_is_fixed_at_start_not_rotated_to_make_motion_positive(self):
        self.reward.start(0, [0, 0, 0.624], [0, 0, math.pi / 2])
        self.assertEqual(self.sample(0.032, x=0.002)["value"], 0)
        self.assertEqual(self.sample(0.064, y=0.002)["value"], 1)

    def test_bad_measurement_or_time_reset_disarms(self):
        self.assertEqual(self.sample(0.032, x=float("nan"))["value"], 0)
        self.assertEqual(self.sample(0.064, x=0.1)["reason"], "not_armed")
        self.reward.start(1, [0, 0, 0.624], [0, 0, 0])
        self.assertEqual(self.sample(0.5)["reason"], "simulation_time_reset")

    def test_disarmed_reward_remains_zero(self):
        self.reward.disarm()
        self.assertEqual(self.sample(0.032, x=0.2)["value"], 0)

    def test_publisher_sends_each_positive_observation_and_never_command_channels(self):
        calls, logs = [], []

        def publish(name, value):
            calls.append((name, value))
            return dict(ok=True, queued_for_hardware=True)

        sender = RewardPublisher(publish, logs.append)
        for value in (0, 0, 1, 1, 0):
            sender.send(dict(value=value, reason="test"))
        self.assertEqual(
            calls,
            [
                (REWARD_INPUT, 0.0),
                (REWARD_INPUT, 1.0),
                (REWARD_INPUT, 1.0),
                (REWARD_INPUT, 0.0),
            ],
        )
        self.assertEqual(len(logs), 4)
        with self.assertRaises(ValueError):
            sender.send(dict(value=0.5))
        with self.assertRaises(RuntimeError):
            RewardPublisher(lambda *a: dict(ok=True)).send(dict(value=1))


if __name__ == "__main__":
    unittest.main()
