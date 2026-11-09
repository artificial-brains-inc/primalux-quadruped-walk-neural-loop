# Spot: local kick loops and learned inhibitory handoffs

A developer-facing Prima-Lux example of four neural motor goals interacting
through measured foot contact. One START initiates a repeating sequence:
**front right → rear left → front left → rear right → front right**.
STOP inhibits the loop. Each leg performs an early push, flexes/advances, then
extends to land. As a leg starts returning, it recruits the next leg’s grounded
push and a small support adjustment before contact releases the next swing.
The support adjustment is directed away from the foot about to lift. Its
physical effect still needs testing on your Webots/Prima-Lux setup.

The teaching question is: **how can one motor goal prepare the next movement,
while contact confirms landing and inhibition controls the handoff?**
The supplied root design uses STDP3/LTP on exactly four inhibitory connections.
A static companion preserves their initial strengths, populations and TNorms for
comparison. Every excitatory connection, kick/reset path and reflex stays static.
Each kick retains its request locally until the kick output recruits termination;
a completion latch prevents a held request from repeating the same kick.

## What runs where

Prima-Lux retains the turn, remembers lift-off, qualifies landing, recruits the
next leg and clears the old turn. Webots supplies four bumper readings and IMU
measurements. Python encodes these observations, measures upright forward
progress for reward and maps neural motor outputs to configured joint targets.
It has no gait clock, phase selector, inverse kinematics or neural ACK wait.

A planted foot cannot immediately pass the turn: the current leg must first have
reported **no contact during its own turn**, then report contact while its neural
return state is active. Contact is collision evidence, not a measurement of load
or completion of a backward push. See [foot feedback](docs/CONTACT.md).

## Requirements

- Linux, Git and Python 3.11 or newer.
- **Webots R2025a, installed separately. The package never installs Webots.**
- Prima-Lux, its developer API key and a reachable device URL.
- SDK 0.4.2; compatible device software with the 0.4.11 reward-type builder
  (Device Manager 0.6.17).
- Internet access to install Python dependencies.

`install.sh` installs the packaged SDK and other Python requirements in `.venv`;
it repairs a missing pip and creates `.env` if needed. Missing Ubuntu Python
prerequisites may require sudo. It does not regenerate your design. Spot PROTOs,
meshes and textures use bundled relative paths. See [requirements](docs/REQUIREMENTS.md).

## Clone and install

Download the bundle supplied with this example. Use its actual filename:

```bash
git clone --branch main "$HOME/Downloads/primalux-spot-kick-loop-ltp.bundle" primalux-spot-kick-loop-ltp
cd primalux-spot-kick-loop-ltp
bash install.sh
source .venv/bin/activate
```

After publication, the repository URL replaces the bundle path. Set `.env`:

```dotenv
AB_DEVICE_URL=http://prima-lux.local:8080
AB_DEVICE_API_KEY=YOUR_DEVICE_DEVELOPER_API_KEY
AB_TELEMETRY=true
WEBOTS_EXECUTABLE=/absolute/path/to/webots
```

`WEBOTS_EXECUTABLE` must name an executable file, not a directory. On the
original development machine it is `/home/r2/webots/webots/webots`.
Keep `.env` out of Git.

## Inspect, build and run the learning graph

The root `brain.abdesign.json` already has the four agreed plastic paths. To select it
explicitly, copy the supplied design:

```bash
cp designs/learning.abdesign.json brain.abdesign.json
ab design --brain brain.abdesign.json --env .env
```

In the Designer, follow START → START_REQUEST → WALK_ENABLED and STEP_FR_REQUEST.
Follow STEP_FR_ACTIVE through the local motor primitive and the foot evidence
back to STEP_FR_HANDOFF_BETA → STEP_RL_REQUEST. Repeat through FL and RR.
Also follow LEG_FR_RETURN_BETA → STEP_RL_PREPARE_HG. This starts the next
grounded push and fixed support offsets before the turn changes. PREPARE retains
the selected support plan through its own swing; the next PREPARE replaces it.
Inspect STEP_FR_BRAKE_BETA → STEP_FR_HANDOFF_BETA: inhibitory feedback,
**strength 0.5**, **STDP3 / GAIT_REWARD / LTP**. The other three legs have the
same local inhibitory learning path. Also follow PUSH_HG → KNEE_PUSH →
KICK_END_BETA: the kick recruits its own termination and sets KICK_DONE.
See [the kick circuit](docs/PUSH.md).

Close the Designer with Ctrl+C. Save/download any Canvas edits before building.
Stop a previously running device brain, then build:

```bash
ab device --env .env stop
ab build brain --brain brain.abdesign.json --env .env
```

Wait for READY, then run:

```bash
ab run -ab --env .env learn
```

Focus the Webots 3D view: **W** starts the loop, **S** stops stepping,
**R** restores upright using the simulator, and **Q** stops and saves the session.
Closing Webots also stops/saves the brain. There is no maximum run duration.
Do not repeatedly press W to sustain walking: the loop is neural.

The large marked floor and tracking view provide a motion reference. Automatic
fall recovery is enabled in `config.json`. It sends STOP, restores the robot,
then may send START; this is simulator assistance, not learned self-righting.
Use the same recovery setting for both comparison conditions. See [recovery](docs/RECOVERY.md).

## Run the static comparison

Stop with Q and wait for saving. Select the static companion and inspect the
same four inhibitory connections with the learning metadata removed:

```bash
cp designs/static.abdesign.json brain.abdesign.json
ab design --brain brain.abdesign.json --env .env
```

Close the Designer, then explicitly rebuild and run:

```bash
ab device --env .env stop
ab build brain --brain brain.abdesign.json --env .env
ab run -ab --env .env walk
```

All four initial inhibitory strengths are **0.5** in both designs. The launcher
rejects `learn` with a static graph and `walk` with a plastic graph before opening
Webots. A run mode never selects or rebuilds a design. The default mode is `learn`.
To return to learning, copy `designs/learning.abdesign.json`, inspect, rebuild and
run `learn` explicitly. The installed design hash must match the saved design.

Run equal simulation durations from the same initial world, with identical
motor/reflex/recovery settings. There are no plastic excitatory or reflex paths,
and no LTD paths. See [comparison procedure](docs/TESTING.md).

Learning changes how strongly the current leg's brake inhibits its handoff Beta.
It cannot bypass the lift-off/landing requirement or change the leg order.
Reward is new upright forward progress: 10 input neurons → 10 high-gamma T10
neurons → 17 dopaminergic T3 neurons. Reward delivery alone does not prove a
weight update or improved walking.

## OPUs and resources

| Role | Rhythm / TNorm | Constructed neurons per population |
| --- | --- | ---: |
| Handoff and its feedback brake | Beta T5 | 2 each |
| Contact and AIR sensory relays / local vetoes | High-gamma T10 | 4 each |
| Retained turn and event helpers | High-gamma T10 | 1 each |
| Anticipatory preparation relay | High-gamma T10 | 2 each |
| Local push relay with preparation input | High-gamma T10 | 3 front / 4 rear |
| Kick termination | Beta T3 | 2 each |
| Kick completion helper / output | High-gamma T10 / output | 1 each |
| Rear local motor drive | Beta T3 | 2 each |
| Regular knee extension | Beta T5 | 24 each |
| Independent corrective reflex | High-gamma T5 | 24 each |
| Reward | Dopaminergic T3 | 17 |

The complete graph has **721 neurons**: 93 external input neurons and 628 other
neurons, across 253 populations. There are four physical foot sensors. Each
reading has four CONTACT neurons and four AIR neurons; the explicit AIR rail
prevents missing asynchronous messages from being interpreted as lift-off.
The remaining inputs are START/STOP/dormant ACK (3), reward (10), and tilt (48).
The legacy ACK circuit is isolated and never used to pace execution.

Strength 0.5 is a multiplier of the SDK's inhibitory reference; it is not a
TNorm or a percentage of neurons. It remains a starting point for physical testing; changes to it
need separate timing and locomotion comparisons. [Design](docs/DESIGN.md) explains the choice and limitations.

## Observe and compare

Each run saves `logs/run-*/settings.json`, `observations.jsonl`,
`contact-inputs.jsonl`, `rewards.jsonl` and `neuron-telemetry.jsonl`.
Settings include the exact design hash, plastic paths and initial strengths.
The console shows active legs, the retained support plan, push motors, raw
contacts and CONTACT_READY flags. The plan is a neural command, not measured
weight transfer. `next_push_before_previous_touchdown_frames` counts early push
outputs only when the previous active foot is measured airborne.
The telemetry observer reads internal neurons without controlling movement.

```bash
python analyze_run.py logs/run-YOUR_RUN_DIRECTORY
python compare_runs.py logs/run-STATIC_DIRECTORY logs/run-LEARNING_DIRECTORY
```

The comparison reports sequence errors, landing-to-next-stage delays, forward
progress, recoveries and observation durations. These are measured outcomes;
neuron firing or eligibility alone is not improvement.

Read [goals and interactions](docs/GOALS.md), [the design](docs/DESIGN.md),
[anticipatory support](docs/SUPPORT.md), [push and return](docs/PUSH.md),
[reflexes](docs/REFLEX.md),
[controller responsibilities](docs/CONTROL.md) and [validation](docs/VALIDATION.md).

Application tests and native-cell checks have been run locally. They do **not**
validate Webots physics, equivalence with the device or learned improvement.
The supplied native checks use synthetic foot evidence, not a simulated gait.

## License

Project code: [Artificial Brains Example Code License](LICENSE).
Bundled Webots assets retain their upstream terms in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
