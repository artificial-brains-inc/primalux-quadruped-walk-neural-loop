"""Receive neural frames, translate actuator outputs, and step Webots once.

There is no gait clock, phase selector, trajectory generator, or command resend
inside the running loop. Physical outcome supplies reward; IMU readings supply
four signed tilt populations. Foot bumpers supply four contact populations.
Reflex leg selection, contact qualification and handoff stay inside the brain.
"""

import json
import os
import time
from contextlib import ExitStack

from controller import Supervisor

from .configuration import ROOT, environment_path, load_config
from .contracts import (
    JOINT_NAMES,
    CONTACT_INPUTS,
    CONTACT_NEURONS,
    JOINTS,
    LEG_NAMES,
    LEGS,
    MOTOR_OUTPUTS,
    PUSH_MOTOR_OUTPUTS,
    REFLEX_MOTOR_OUTPUTS,
    REFLEX_OUTPUTS,
    REWARD_CLASSIFICATION,
    REWARD_INPUT_NEURONS,
    validate_channels,
)
from .decoder import joint_speeds, joint_targets
from .contact import clear_contacts, encode_contacts, setup_contact_sensors
from .exchange import CommandExchange
from .live_inputs import LiveInputs
from .reward import ProgressReward, RewardPublisher
from .recovery import Recovery
from .reflex import TiltPublisher
from .neuron_recording import NeuronRecorder
from .transport import EventBuffer, StopRequested


def write_state(state, **fields):
    path = ROOT / "logs/run_state.json"
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(state=state, time=time.time(), **fields)) + "\n")
    tmp.replace(path)


def main():
    from ab import ABClient

    from .application import saved_design, verify_installed
    from ab_sdk.design_submit import design_sha256
    from .evaluation import summarize

    config = load_config()
    mode = os.environ.get("SPOT_RUN_MODE", "learn")
    if mode not in ("learn", "walk", "rhythm"):
        raise ValueError("Unknown Spot mode")
    body = Supervisor()
    robot_node = body.getSelf()
    if robot_node is None:
        raise RuntimeError("Spot recovery requires supervisor TRUE in the demo world")
    dt = config["physics_step_ms"]
    keyboard = body.getKeyboard()
    keyboard.enable(dt)
    motors, sensors, speeds = {}, {}, {}
    for leg in LEGS:
        for joint in JOINTS:
            key = (leg, joint)
            prefix = LEG_NAMES[leg] + " " + JOINT_NAMES[joint]
            motors[key] = body.getDevice(prefix + " motor")
            sensors[key] = body.getDevice(prefix + " sensor")
            sensors[key].enable(dt)
            settings = config["joint_targets"][joint]
            speed = min(settings["speed_rad_s"], motors[key].getMaxVelocity())
            speeds[key] = speed
            motors[key].setVelocity(speed)
            side = "left" if leg in ("FL", "RL") else "right"
            motors[key].setPosition(settings["neutral_" + side])
    gps, imu, gyro = [body.getDevice(name) for name in ("gps", "inertial unit", "gyro")]
    for device in (gps, imu, gyro):
        device.enable(dt)
    contact_sensors = setup_contact_sensors(body, dt)
    directory = (
        ROOT
        / "logs"
        / ("run-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(time.time_ns()))
    )
    directory.mkdir(parents=True)
    design_hash = design_sha256(saved_design())
    (directory / "settings.json").write_text(
        json.dumps(
            dict(
                config=config,
                mode=mode,
                design_sha256=design_hash,
                project_root=str(ROOT),
                reflex_motor_outputs=list(REFLEX_MOTOR_OUTPUTS),
                push_motor_outputs=list(PUSH_MOTOR_OUTPUTS),
                reward_classification=REWARD_CLASSIFICATION,
                reward_input_neurons=REWARD_INPUT_NEURONS,
                contact_input_neurons=CONTACT_NEURONS * len(CONTACT_INPUTS),
                contact_inputs=CONTACT_INPUTS,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"[SPOT] Fast reflex outputs: {len(REFLEX_MOTOR_OUTPUTS)}; "
        f"pre-swing push outputs: {len(PUSH_MOTOR_OUTPUTS)}; "
        f"reward input: {REWARD_INPUT_NEURONS} neurons; "
        f"foot contacts: {len(contact_sensors)} sensors / {CONTACT_NEURONS} neurons each; "
        f"reward class: dopaminergic T3 / release LTP / support LTP; "
        f"design: {design_hash}; project: {ROOT}",
        flush=True,
    )
    client = session = recorder = None
    failed = False
    started = time.monotonic()
    rows = []
    reward = ProgressReward(config["reward"])
    recovery = Recovery(config["recovery"], config["reward"])

    def advance():
        if (ROOT / ".stop-request").exists():
            raise StopRequested("Stop requested")
        if body.step(dt) == -1:
            raise StopRequested("Webots closed")

    try:
        # One neutral startup step makes measured positions available.
        advance()
        verify_installed()
        client = ABClient.from_env(env_path=environment_path())
        session = client.start_from_env(env_path=environment_path())
        recorder = NeuronRecorder(
            directory / "neuron-telemetry.jsonl", environment_path()
        )
        recorder.start()
        with (
            (directory / "native-outputs.jsonl").open("x", buffering=1) as native,
            (directory / "commands.jsonl").open("x", buffering=1) as commands,
            (directory / "observations.jsonl").open("x", buffering=1) as observations,
            (directory / "rewards.jsonl").open("x", buffering=1) as rewards,
            (directory / "tilt-inputs.jsonl").open("x", buffering=1) as tilt_log,
            (directory / "contact-inputs.jsonl").open("x", buffering=1) as contact_log,
            ExitStack() as workers,
        ):
            events = EventBuffer(
                (ROOT / ".stop-request").exists,
                timeout_seconds=config["output_timeout_seconds"],
                record=lambda e: native.write(json.dumps(e) + "\n"),
            )
            session.on_output(events.on_output)
            session.on_control(events.on_control)

            def record_command(event):
                commands.write(
                    json.dumps(dict(event, wall_seconds=time.monotonic() - started))
                    + "\n"
                )
                kind, action = event["kind"], event.get("action", "").upper()
                if kind == "command_queued":
                    print(f"[SPOT] {action} queued; no neural ACK handshake.", flush=True)
                elif kind == "command_confirmed":
                    print(
                        f"[SPOT] {action} confirmed: WALK_ENABLED={event['walk']}, "
                        f"REST_ACTIVE={event['rest']}.", flush=True,
                    )

            inputs = workers.enter_context(LiveInputs(
                session.publish_sensor_frame,
                lambda: events.stats()["last_received_step"], config["reflex"],
                tilt_record=lambda e: tilt_log.write(json.dumps(e) + "\n"),
                reward_record=lambda e: rewards.write(json.dumps(e) + "\n"),
                contact_record=lambda e: contact_log.write(json.dumps(e) + "\n"),
            ))
            exchange = CommandExchange(
                inputs.command, config["command_timeout_seconds"], record=record_command,
            )
            exchange.initialize_inputs()
            exchange.command("stop")
            inputs.feedback([0, 0, 0], dict(value=0, reason="startup"), suspended=True)
            event = events.wait_one(time.monotonic() + config["output_timeout_seconds"])
            action = "stop"
            pressed_before = set()
            tick = 0
            write_state(
                "RUNNING", mode=mode, result_dir=str(directory.relative_to(ROOT))
            )
            print(
                "[SPOT] Standing. Focus the 3D view: W = walk, S = stop stepping, "
                "R = recover upright, Q = Stop/save. "
                f"Automatic recovery: {config['recovery']['automatic']}.",
                flush=True,
            )
            while True:
                events.check_health()
                inputs.check_health()
                confirmed = exchange.observe(event)
                channels = validate_channels(event)
                recovery_frame = recovery.active
                recovery_state = recovery.state
                recovery_event = recovery.update(
                    body.getTime(),
                    stopped=(
                        exchange.pending_action is None
                        and channels["REST_ACTIVE"] == 1
                        and channels["WALK_ENABLED"] == 0
                        and not any(channels[k] for k in MOTOR_OUTPUTS)
                    ),
                    xyz=gps.getValues(),
                    rpy=imu.getRollPitchYaw(),
                )
                if recovery_event == "restore":
                    # Restore this robot and its joints only. The neural session,
                    # learned weights, other objects and simulation time continue.
                    robot_node.loadState("__init__")
                    robot_node.resetPhysics()
                    for key, motor in motors.items():
                        motor.setVelocity(speeds[key])
                    print("[SPOT] Upright pose restored; settling in REST.", flush=True)
                elif recovery_event == "ready":
                    print("[SPOT] Recovery complete; Spot is upright.", flush=True)
                if confirmed == "start" and mode == "learn" and not recovery_frame:
                    reward.start(body.getTime(), gps.getValues(), imu.getRollPitchYaw())
                if (
                    mode != "learn"
                    or recovery_frame
                    or exchange.pending_action is not None
                    or not channels["WALK_ENABLED"]
                    or channels["REST_ACTIVE"]
                ):
                    reward.disarm()
                targets = joint_targets(
                    event, config, rhythm_only=(mode == "rhythm" or recovery_frame)
                )
                commanded_speeds = joint_speeds(
                    event, config, rhythm_only=(mode == "rhythm" or recovery_frame)
                )
                for key, q in targets.items():
                    commanded_speeds[key] = min(
                        commanded_speeds[key], motors[key].getMaxVelocity()
                    )
                    motors[key].setVelocity(commanded_speeds[key])
                    motors[key].setPosition(q)
                advance()
                xyz, rpy = list(gps.getValues()), list(imu.getRollPitchYaw())
                evidence = reward.sample(body.getTime(), xyz, rpy)
                contact_values = {leg: sensor.getValue() for leg, sensor in contact_sensors.items()}
                feedback_suspended = recovery_frame
                tilt_inputs = inputs.feedback(
                    rpy, evidence, suspended=feedback_suspended, contacts=contact_values,
                    tilt_suspended=(mode == "rhythm"),
                    native_step=event["step"], simulation_time=body.getTime(),
                )
                record = dict(
                    native_step=event["step"],
                    tick=tick,
                    simulation_time=body.getTime(),
                    wall_seconds=time.monotonic() - started,
                    mode=mode,
                    requested_command=action,
                    command_sequence=exchange.sequence,
                    pending_command=exchange.pending_action,
                    recovery_state=recovery.state
                    if recovery_event == "restore"
                    else recovery_state,
                    recovery_event=recovery_event,
                    recovery_count=recovery.count,
                    outputs=channels,
                    joint_position_rad={
                        "_".join(k): s.getValue() for k, s in sensors.items()
                    },
                    joint_target_rad={"_".join(k): q for k, q in targets.items()},
                    joint_speed_limit_rad_s={
                        "_".join(k): v for k, v in commanded_speeds.items()
                    },
                    body_xyz_m=xyz,
                    body_rpy_rad=rpy,
                    tilt_inputs=tilt_inputs,
                    foot_contact=contact_values,
                    contact_inputs=encode_contacts(contact_values, suspended=feedback_suspended),
                    reward=evidence,
                    gyro_rad_s=list(gyro.getValues()),
                    queued_native_frames=events.stats()["queued_frames"],
                    input_transport=inputs.stats(),
                )
                observations.write(json.dumps(record) + "\n")
                rows.append(record)
                if tick % 30 == 0:
                    print(
                        "[SPOT] "
                        + json.dumps(
                            dict(
                                step=event["step"],
                                walk=channels["WALK_ENABLED"],
                                rest=channels["REST_ACTIVE"],
                                start_request=channels["START_REQUEST"],
                                stop_request=channels["STOP_REQUEST"],
                                a=channels["PHASE_A_OUT"],
                                b=channels["PHASE_B_OUT"],
                                pending=exchange.pending_action,
                                recovery=record["recovery_state"],
                                reflexes=[
                                    name for name in REFLEX_OUTPUTS if channels[name]
                                ],
                                reflex_motors=[
                                    name
                                    for name in REFLEX_MOTOR_OUTPUTS
                                    if channels[name]
                                ],
                                queued_frames=record["queued_native_frames"],
                                contacts=record["foot_contact"],
                                contact_ready=[leg for leg in LEGS if channels[f"LEG_{leg}_CONTACT_READY"]],
                                xyz=record["body_xyz_m"],
                            )
                        ),
                        flush=True,
                    )
                tick += 1
                pressed = set()
                key = keyboard.getKey()
                while key != -1:
                    pressed.add(key & 0xFFFF)
                    key = keyboard.getKey()
                new = pressed - pressed_before
                pressed_before = pressed
                if ord("Q") in new:
                    raise StopRequested("User ended the session")
                requested = (
                    "stop" if ord("S") in new else "start" if ord("W") in new else None
                )
                manual_recovery = ord("R") in new
                fallen = recovery.detect_fall(body.getTime(), xyz, rpy)
                if recovery.active:
                    if requested is not None:
                        # STOP is already in progress. S cancels auto-resume;
                        # W requests a single START only after stable recovery.
                        recovery.resume = requested == "start"
                        print(
                            f"[SPOT] Recovery will {'resume walking' if recovery.resume else 'remain in REST'}.",
                            flush=True,
                        )
                    requested = None
                elif manual_recovery or fallen:
                    reason = "R key" if manual_recovery else "fall detected"
                    recovery.begin(
                        body.getTime(),
                        resume=(
                            requested == "start"
                            or (requested is None and action == "start")
                        ),
                        reason=reason,
                    )
                    record_command(dict(kind="recovery_requested", reason=reason))
                    print(f"[SPOT] Recovery: {reason}; requesting STOP.", flush=True)
                    requested = "stop"
                elif (
                    recovery_event == "ready" and requested is None and recovery.resume
                ):
                    requested = "start"
                if requested is not None:
                    reward.disarm()
                    if (requested == "start" and ord("W") in new) or (
                        requested == "stop" and ord("S") in new
                    ):
                        key_name = "W" if requested == "start" else "S"
                        record_command(
                            dict(
                                kind="keyboard_command", action=requested, key=key_name
                            )
                        )
                        print(f"[SPOT] {key_name} received.", flush=True)
                    exchange.command(requested)
                    action = requested
                # Every native frame remains available for actuation. Input
                # HTTP work runs separately; neither side waits for neural ACK.
                event = events.wait_one(
                    time.monotonic() + config["output_timeout_seconds"]
                )
    except (StopRequested, KeyboardInterrupt):
        print("Stopping Spot session.", flush=True)
    except Exception as exc:
        failed = True
        write_state("ERROR", error_type=type(exc).__name__, message=str(exc))
        raise
    finally:
        for motor in motors.values():
            try:
                motor.setVelocity(0.0)
            except Exception:
                pass
        try:
            if session is not None:
                try:
                    # The log streams may already be closed. Stop/save must still
                    # execute if the final reward clear fails during disconnect.
                    RewardPublisher(session.publish_reward).send(
                        dict(value=0, reason="session_end"), force=True
                    )
                    TiltPublisher(session.publish_sensor_frame, config["reflex"]).send(
                        [0, 0, 0], suspended=True, force=True
                    )
                    clear_contacts(session.publish_sensor_frame)
                finally:
                    session.stop()
            write_state(
                "ERROR" if failed else "STOPPED",
                neural_stop_confirmed=session is not None,
            )
        except Exception as exc:
            failed = True
            write_state("ERROR", neural_stop_confirmed=False, message=str(exc))
            raise
        finally:
            if recorder is not None:
                recorder.stop()
            if client is not None:
                client.close()
            report = summarize(rows)
            report.update(mode=mode, error=failed)
            (directory / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
            print("[RESULT] " + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
