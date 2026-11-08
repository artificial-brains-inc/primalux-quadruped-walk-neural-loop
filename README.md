# Spot: inhibitory coordination and support reflexes

A developer teaching example for Prima-Lux and Webots. One walking nucleus drives
two neural phase pathways. Each phase inhibits the other; its downstream RELEASE
inhibits its own inhibitor, making room for the opposite phase. STDP3 modulates
those inhibitory paths using one reward signal from actual body movement. Four local
high-gamma reflexes respond to body tilt, veto knee flexion, extend the supporting
leg and terminate through their own inhibitory return paths.

**A and B are phases; the robot has four leg motor cortices.** Each leg has three
actuators with opposing POS/NEG motor populations: 24 local motor populations.

| Phase | Swing pair | Supporting pair |
| --- | --- | --- |
| A | Front-left + rear-right | Front-right + rear-left |
| B | Front-right + rear-left | Front-left + rear-right |

There are **eight external input neurons total**: START, STOP, ACK, reward,
and four signed roll/pitch measurements. The four added neurons are physical
feedback; leg selection and burst cutoff are neural.
No phase clock, joint error vector or gait generator runs in Python. The adapter
maps local motor outputs to Webots joint targets, measures physical outcome, and
publishes reward and current tilt evidence. Webots position servos track the targets.

This package passes construction and local integration tests. **Learned walking
has not been demonstrated here.** The isolated command check exercises START/STOP/restart; neural gait handoff,
reward timing and physical coordination need testing together on Prima-Lux and Webots.

## What you learn

- Build a retained goal and an opposing STOP/REST goal.
- Use inhibition of an inhibitor to release a competing action.
- Share phase preparation across four leg motor cortices.
- Add a local support reflex that overrides flexion, then inhibits itself and
  clears its bistable extension output.
- Choose which connections should learn and which must retain fixed semantics.
- Define reward from an outcome, then compare learning with a static circuit.

Start with [goals and interactions](docs/GOALS.md), then the
[neural design](docs/DESIGN.md) and [control boundary](docs/CONTROL.md).

## Requirements

- Linux desktop, Git and Python 3.11 or newer.
- **Webots R2025a installed separately.** The package never installs Webots.
- Prima-Lux, its developer API key and a reachable device address.
- **Device Manager 0.6.17 with the compatible 0.4.11 builder on Prima-Lux**, as
  required by SDK 0.4.2's reward-type support. Updating this project's Python
  environment does not update the device.
- Internet access for Python dependency installation.

The installer creates or repairs `.venv`, installs **SDK 0.4.2**, and creates `.env`
if missing. On Ubuntu it can install missing Python prerequisites using sudo.
The project includes Spot's PROTOs, meshes and textures with local relative paths.
It does not depend on Webots sample directories or download model assets at Run.
[Requirements and troubleshooting](docs/REQUIREMENTS.md).

## Clone and install

```bash
git clone "$HOME/Downloads/primalux-spot-learning-reflex.bundle" primalux-spot-learning
cd primalux-spot-learning
bash install.sh
source .venv/bin/activate
```

After publication, substitute the repository URL for the bundle path. Edit `.env`:

```dotenv
AB_DEVICE_URL=http://prima-lux.local:8080
AB_DEVICE_API_KEY=YOUR_DEVICE_DEVELOPER_API_KEY
AB_TELEMETRY=true
WEBOTS_EXECUTABLE=/absolute/path/to/webots
```

The Webots setting must name an executable file, not a directory. An exported
`WEBOTS_EXECUTABLE` also works. Keep credentials out of Git.

## See the design

```bash
ab design --brain brain.abdesign.json --env .env
```

Follow START → START_REQUEST → START_REQUEST_HG → WALK_ENABLED → WALK_NUCLEUS
→ WALK_DRIVE, then both phase pathways. START_REQUEST captures one input event;
its helper retains the request until WALK takes over and clears it. STOP mirrors
this path. Opposite command cues cancel pending requests.
Follow A_RELEASE back to A_INHIBITOR and A_INHIBITOR across to B. B mirrors A.
Inspect the four leg columns below the phase core. Each has POS/NEG populations
for ABD, HIP and KNEE.

The console includes `start_request` and `stop_request` readouts to distinguish
request capture from goal confirmation. These readouts do not drive the body.

Inspect an inhibitory connection's learning settings: **STDP3**, reward population
**GAIT_REWARD**, reward type **LTP**. Trace the separate reward input through its
High-Gamma relay to that dopaminergic population. START, STOP, ACK and the support reflexes stay static.

Below the motor columns, follow TILT_ROLL/PITCH → REFLEX → ACTIVE → GUARD
→ RESET, including the inhibitory return. See [support reflexes](docs/REFLEX.md).

Close the Designer with Ctrl+C before continuing in that terminal. If editing on
the Canvas, save/download and replace `brain.abdesign.json` before Build. Install
and Run use the saved graph and never regenerate it.

## Build the brain

```bash
ab device --env .env stop
ab build brain --brain brain.abdesign.json --env .env
```

**Wait for READY. The reflex graph requires a new Build.** An older installed
brain will fail the package's design-identity check.

The saved graph has 578 total neurons, including eight external input neurons,
118 populations, 435 connections and approximately 0.54 MiB of connection matrices.
Of those connections, 66 inhibitory paths use STDP3. These are connections, not
66 extra OPUs. [Aggregate resource check](docs/RESOURCE_CHECK.json).
The device Build remains authoritative. This is a new design: do not assume
learned weights from the previous installed graph migrate to it.

## Run and learn

```bash
ab run -ab --env .env learn
```

Focus the Webots 3D view:

- **W:** request walking. Reward becomes eligible after exclusive WALK confirmation.
- **S:** clear reward and request STOP/REST; the neural session remains running.
- **R:** restore Spot upright at the starting position. Resume after settling if
  walking was requested. Press S during recovery to remain in REST.
- **Q:** end the session and trigger Prima-Lux Stop/save.

Automatic fall recovery is enabled. A tilt of at least 1.05 rad (about 60 degrees)
or body height below 0.30 m for 0.5 simulation seconds requests recovery. The
adapter requests neural STOP, waits for REST and quiet motor outputs, restores
Spot's initial body/joint state and zeroes its momentum. After one upright second
it sends one START if walking should resume. The brain session and learned weights
are retained; recovery supplies no reward. This is simulator assistance, not
learned self-righting. Set `recovery.automatic` to `false` in `config.json` for
unassisted trials; R still works. [Recovery details](docs/RECOVERY.md).

The support reflex begins from roll or pitch beyond **0.15 rad (about 8.6°)**.
Pure sideways tilt recruits the two legs on that side; combined forward/sideways
tilt recruits the corresponding corner. These relationships are wired in the
brain. Each reflex uses High-Gamma T10 and static inhibition strength 4; its reset
also clears the knee extension output. It does not increase motor speed or torque.
The isolated check produced five-frame bursts, but actual gait interaction and
balance still need the live test. Set `reflex.enabled` to `false` in `config.json`
to compare without tilt evidence; that setting applies on the next Run.

The arena is 30 × 30 metres with a **1 metre grid**, heavier lines every 5 metres,
a blue starting square and a red forward (+X) line with arrows and metre labels.
The five onboard camera devices are removed; GPS and orientation sensors remain.
The wider opening view looks toward Spot from the front-left and follows its
position with an upright horizon. The floor markings stay fixed in the world.

Each native neural frame advances **64 ms of simulated body time**, using four
16 ms physics substeps. Webots opens in fast mode with rendering enabled, so it
does not impose realtime pacing on top of the neural stream. The adapter still
consumes each frame once, in order, and uses the current neural motor outputs.
A five-frame motor command now has 0.32 simulated seconds instead of 0.16 to
move the joint. This is actuator/simulation calibration; it does not extend a
neural output or guarantee a completed stroke. [Measured findings and timing](TIMING.md).

Startup is standing/resting. The console separately reports key receipt, command
publication, transport ACK and WALK/REST confirmation. After ACK, the body advances
once per native neural frame while waiting for confirmation. The input event is not held by the device: the neural
request latch supplies the continuing command drive. No command resends
or host phase switching occur. Holding W does not publish on every frame.

Reward is **1** for new forward progress while upright and **0** otherwise.
It uses GPS and orientation, a fixed heading captured at START, and a forward
high-water mark so retracing old distance earns no repeated reward. Initial
thresholds are 0.02 m/s forward speed, roll/pitch within 0.35 rad and body height
at least 0.45 m. They are editable outcome criteria in `config.json`.

Gait inhibition begins at reference strength 1 instead of a strong fixed veto.
STDP3 uses local eligibility and reward to modulate those connections. LTP follows
eligibility; it does not guarantee every inhibitory weight increases. Zero reward
is not a negative punishment. Learning cannot fix a circuit that produces no
useful activity or movement to evaluate.

The outcome criterion can reward upright sliding; it does not establish foot
contact or balance. Inspect body motion and logs before calling the result walking.

## Inspect without external reward

```bash
ab run -ab --env .env rhythm
```

`rhythm` runs the brain with neutral joint targets and no positive reward events.
`ab run -ab --env .env walk` applies motor outputs with no positive external reward events. Neither is a guaranteed frozen-weight baseline for a previously active
plastic graph. [Testing](docs/TESTING.md) includes an explicitly static comparison.
End each session before starting another.

## Stop and inspect results

Q, Ctrl+C in the launching terminal, or closing Webots triggers Prima-Lux Stop/save.
Wait for **Prima-Lux Stop/save confirmed**. From another activated terminal:

```bash
ab device --env .env stop
```

Each `logs/run-.../` directory contains:

- `native-outputs.jsonl`: received native frames, including command waits.
- `commands.jsonl`: key receipt, publication, ACK and goal confirmation.
- `observations.jsonl`: applied frame, resulting joint/body measurements and reward evidence.
- `rewards.jsonl`: accepted reward events from qualifying physical observations.
- `tilt-inputs.jsonl`: simultaneous tilt evidence and publication duration.
  Observations also include all four `REFLEX_*_ACTIVE` readouts; summary reports
  their active frames and entries. These are readouts, not measured spike counts.
- `summary.json`: phase entries, motor overlaps, reward frames, progress and STOP checks.
- `settings.json`: mode and configuration used for this run.

```bash
python analyze_run.py logs/run-YOUR_RUN_DIRECTORY
```

These logs measure behavior and external reward delivery; they do not report
individual learned weights. Use device telemetry where available to inspect the
neural activity. [Validation and limits](docs/VALIDATION.md).

## Edit the example

`design_brain.py` authors the public graph. Regenerate only when intentionally
replacing the saved design; preserve any Canvas edits first:

```bash
python design_brain.py
ab design --brain brain.abdesign.json --env .env
```

Close Designer, then run the separate SDK Build and Run commands above. Neural
changes require Build. Actuator, timing and reward criteria in `config.json`
apply on the next Run. They do not set a neural gait period.

## License

Original code, graph and documentation use the included
[Artificial Brains Example Code License](LICENSE). Bundled Webots assets retain
their upstream licenses and attribution in [third-party notices](THIRD_PARTY_NOTICES.md).
