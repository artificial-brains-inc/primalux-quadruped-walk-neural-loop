"""Receive neural frames, translate actuator outputs, and step Webots once.

There is no gait clock, phase selector, trajectory generator, or input resend
inside the running loop. Physical outcome supplies one binary reward in learn mode.
"""

import json
import os
import time

from controller import Robot

from .configuration import ROOT, environment_path, load_config
from .contracts import JOINT_NAMES, JOINTS, LEG_NAMES, LEGS, validate_channels
from .decoder import joint_targets
from .exchange import CommandExchange
from .reward import ProgressReward, RewardPublisher
from .transport import EventBuffer, StopRequested


def write_state(state, **fields):
    path = ROOT / "logs/run_state.json"
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(state=state, time=time.time(), **fields)) + "\n")
    tmp.replace(path)


def main():
    from ab import ABClient

    from .application import verify_installed
    from .evaluation import summarize

    config = load_config()
    mode = os.environ.get("SPOT_RUN_MODE", "learn")
    if mode not in ("learn", "walk", "rhythm"):
        raise ValueError("Unknown Spot mode")
    body = Robot()
    dt = config["physics_step_ms"]
    keyboard = body.getKeyboard()
    keyboard.enable(dt)
    motors, sensors = {}, {}
    for leg in LEGS:
        for joint in JOINTS:
            key = (leg, joint)
            prefix = LEG_NAMES[leg] + " " + JOINT_NAMES[joint]
            motors[key] = body.getDevice(prefix + " motor")
            sensors[key] = body.getDevice(prefix + " sensor")
            sensors[key].enable(dt)
            settings = config["joint_targets"][joint]
            speed = min(settings["speed_rad_s"], motors[key].getMaxVelocity())
            motors[key].setVelocity(speed)
            side = "left" if leg in ("FL", "RL") else "right"
            motors[key].setPosition(settings["neutral_" + side])
    gps, imu, gyro = [body.getDevice(name) for name in ("gps", "inertial unit", "gyro")]
    for device in (gps, imu, gyro):
        device.enable(dt)
    directory = (
        ROOT
        / "logs"
        / ("run-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(time.time_ns()))
    )
    directory.mkdir(parents=True)
    (directory / "settings.json").write_text(
        json.dumps(dict(config=config, mode=mode), indent=2) + "\n"
    )
    client = session = None
    failed = False
    started = time.monotonic()
    rows = []
    reward = ProgressReward(config["reward"])

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
        with (
            (directory / "native-outputs.jsonl").open("x", buffering=1) as native,
            (directory / "commands.jsonl").open("x", buffering=1) as commands,
            (directory / "observations.jsonl").open("x", buffering=1) as observations,
            (directory / "rewards.jsonl").open("x", buffering=1) as rewards,
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
                if kind == "command_sent":
                    print(
                        f"[SPOT] {action} sent; waiting for transport ACK.", flush=True
                    )
                elif kind == "command_ack":
                    print(
                        f"[SPOT] {action} ACK received; waiting for WALK/REST confirmation.",
                        flush=True,
                    )
                elif kind == "command_confirmed":
                    print(
                        f"[SPOT] {action} confirmed: WALK_ENABLED={event['walk']}, "
                        f"REST_ACTIVE={event['rest']}; command inputs cleared.",
                        flush=True,
                    )

            exchange = CommandExchange(
                session.publish_sensor_frame,
                events,
                config["ack_timeout_seconds"],
                record=record_command,
            )
            exchange.initialize_inputs()
            reward_sender = RewardPublisher(
                session.publish_reward,
                record=lambda e: rewards.write(json.dumps(e) + "\n"),
            )
            reward_sender.send(dict(value=0, reason="startup"), force=True)
            event = exchange.command("stop")
            action = "stop"
            pressed_before = set()
            tick = 0
            write_state(
                "RUNNING", mode=mode, result_dir=str(directory.relative_to(ROOT))
            )
            print(
                "[SPOT] Standing. Focus the 3D view: W = walk, S = stop stepping, Q = Stop/save.",
                flush=True,
            )
            while time.monotonic() - started < config["max_run_wall_seconds"]:
                events.check_health()
                confirmed = exchange.observe(event)
                channels = validate_channels(event)
                if confirmed == "start" and mode == "learn":
                    reward.start(body.getTime(), gps.getValues(), imu.getRollPitchYaw())
                if (
                    mode != "learn"
                    or exchange.pending_action is not None
                    or not channels["WALK_ENABLED"]
                    or channels["REST_ACTIVE"]
                ):
                    reward.disarm()
                targets = joint_targets(event, config, rhythm_only=(mode == "rhythm"))
                for key, q in targets.items():
                    motors[key].setPosition(q)
                advance()
                xyz, rpy = list(gps.getValues()), list(imu.getRollPitchYaw())
                evidence = reward.sample(body.getTime(), xyz, rpy)
                reward_sender.send(
                    evidence, native_step=event["step"], simulation_time=body.getTime()
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
                    outputs=channels,
                    joint_position_rad={
                        "_".join(k): s.getValue() for k, s in sensors.items()
                    },
                    joint_target_rad={"_".join(k): q for k, q in targets.items()},
                    body_xyz_m=xyz,
                    body_rpy_rad=rpy,
                    reward=evidence,
                    gyro_rad_s=list(gyro.getValues()),
                    queued_native_frames=events.stats()["queued_frames"],
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
                                a=channels["PHASE_A_OUT"],
                                b=channels["PHASE_B_OUT"],
                                pending=exchange.pending_action,
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
                if requested is not None:
                    reward.disarm()
                    reward_sender.send(
                        dict(value=0, reason="command_" + requested),
                        native_step=event["step"],
                        simulation_time=body.getTime(),
                    )
                    record_command(
                        dict(
                            kind="keyboard_command",
                            action=requested,
                            key="W" if requested == "start" else "S",
                        )
                    )
                    print(
                        f"[SPOT] {'W' if requested == 'start' else 'S'} received.",
                        flush=True,
                    )
                    # Only transport ACK blocks here. Neural goal confirmation
                    # is observed above while frame-synchronized physics continues.
                    event = exchange.command(requested)
                    action = requested
                else:
                    # No periodic stimulus. One next native frame, one step.
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
            if client is not None:
                client.close()
            report = summarize(rows)
            report.update(mode=mode, error=failed)
            (directory / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
            print("[RESULT] " + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
