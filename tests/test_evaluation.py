import unittest

from robot.contracts import OUTPUT_SIZES
from robot.evaluation import summarize


def row(sequence, action, **outputs):
    channels = {k: 0 for k in OUTPUT_SIZES}
    channels.update(outputs)
    return dict(
        command_sequence=sequence,
        requested_command=action,
        outputs=channels,
        body_xyz_m=[0, 0, 0.6],
        body_rpy_rad=[0, 0, 0],
        queued_native_frames=0,
        simulation_time=0,
        wall_seconds=0,
    )


class EvaluationTests(unittest.TestCase):
    def test_recovery_teleport_is_excluded_from_displacement(self):
        rows = [row(2, "start") for _ in range(5)]
        for r, x in zip(rows, [5, 6, 0, 0, 0.5]):
            r["body_xyz_m"][0] = x
        rows[2].update(recovery_state="settling", recovery_count=1)
        rows[3].update(recovery_state="settling", recovery_count=1)
        rows[4].update(recovery_state="idle", recovery_count=1)
        report = summarize(rows)
        self.assertEqual(report["displacement_xyz_m"][0], 1)
        self.assertEqual(report["recoveries"], 1)
        self.assertEqual(report["recovery_frames"], 2)

    def test_request_and_release_readouts_are_measured_separately(self):
        report = summarize(
            [
                row(1, "start", WALK_ENABLED=1, PHASE_A_REQUEST=1),
                row(1, "start", WALK_ENABLED=1, PHASE_A_RELEASE_OUT=1),
                row(1, "start", PHASE_B_REQUEST=1),
            ]
        )
        counts = report["diagnostic_active_walking_frames"]
        self.assertEqual(counts["WALK_ENABLED"], 2)
        self.assertEqual(counts["PHASE_A_REQUEST"], 1)
        self.assertEqual(counts["PHASE_A_RELEASE_OUT"], 1)
        self.assertEqual(counts["PHASE_B_REQUEST"], 1)
        self.assertEqual(counts["PHASE_B_RELEASE_OUT"], 0)

    def test_startup_stop_does_not_claim_walking_stop_tested(self):
        report = summarize(
            [
                row(1, "stop"),
                row(2, "start", PHASE_A_OUT=1),
                row(2, "start"),
                row(2, "start", PHASE_A_OUT=1),
                row(2, "start", PHASE_B_OUT=1),
            ]
        )
        self.assertEqual(report["phase_a_entries"], 2)
        self.assertEqual(report["phase_b_entries"], 1)
        self.assertEqual(report["repeated_same_phase_entries"], 1)
        self.assertEqual(report["alternating_phase_entries"], 1)
        self.assertEqual(report["stop_commands_observed_after_walking"], 0)

    def test_overlap_is_measured_without_changing_motor_outputs(self):
        rows = [
            row(1, "stop"),
            row(2, "start", FL_HIP_POS=1, FL_HIP_NEG=1, PHASE_A_REQUEST=1),
            row(3, "stop"),
            row(4, "start"),
        ]
        report = summarize(rows)
        self.assertEqual(report["motor_antagonist_overlap_frames"], 1)
        self.assertEqual(report["motor_antagonist_overlap_by_joint"]["FL_HIP"], 1)
        self.assertEqual(
            report["diagnostic_active_walking_frames"]["PHASE_A_REQUEST"], 1
        )
        self.assertEqual(report["stop_commands_observed_after_walking"], 1)
        self.assertEqual(rows[1]["outputs"]["FL_HIP_POS"], 1)
        self.assertEqual(rows[1]["outputs"]["FL_HIP_NEG"], 1)

    def test_patterns_are_counted_from_motor_outputs_not_phase_lamps(self):
        a = row(2, "start", WALK_ENABLED=1, PHASE_B_OUT=1)
        for leg, side in (("FL", "NEG"), ("RR", "NEG"), ("FR", "POS"), ("RL", "POS")):
            for joint in ("HIP", "KNEE"):
                a["outputs"][f"{leg}_{joint}_{side}"] = 1
        all_flex = row(
            2,
            "start",
            WALK_ENABLED=1,
            **{f"{leg}_KNEE_POS": 1 for leg in ("FL", "FR", "RL", "RR")},
        )
        left = row(2, "start", WALK_ENABLED=1, FL_KNEE_POS=1, RL_KNEE_POS=1)
        pending = row(2, "start", WALK_ENABLED=1, FL_KNEE_POS=1, RL_KNEE_POS=1)
        pending["pending_command"] = "start"
        report = summarize([a, all_flex, left, pending])
        self.assertEqual(report["confirmed_walking_frames"], 3)
        self.assertEqual(
            report["complete_diagonal_motor_pattern_frames"], dict(A=1, B=0)
        )
        self.assertEqual(report["all_four_knees_flexing_frames"], 1)
        self.assertEqual(
            report["same_side_only_knee_flexion_frames"], dict(left=1, right=0)
        )


if __name__ == "__main__":
    unittest.main()
