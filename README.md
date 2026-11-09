# Spot: contact-guided walking with inhibitory LTP

A developer teaching example for Prima-Lux and Webots. Each leg first gives a
small extension push, then flexes and advances, then returns to support. Neural
activity sequences the movements; independent tilt reflexes can override a
leg's knee motion.

Learning is **STDP3 with LTP only on four inhibitory release-feedback paths**.
Every excitatory connection is static, including the normal support-to-extension
path. All contact and reflex connections are static as well.

| Macro state | First | Then |
| --- | --- | --- |
| A | Front-right push → swing → return | Rear-left push → swing → return |
| B | Front-left push → swing → return | Rear-right push → swing → return |

Each foot-pad bumper has a 10 g Physics body attached to the forearm by Webots.
This allows its collider to transmit ground forces to the leg. The original pad
shape and placement are preserved; the four pads add 40 g to the model.

The return pathway directly activates final knee extension and clears flexion.
Four foot-pad TouchSensors now supply measured contact. The neural handoff
needs both the local return state and contact at that foot: front confirmation
recruits its diagonal rear partner; rear confirmation recruits the phase handoff.
Extension remains available while waiting for contact. Contact indicates a pad
collision, not the amount of weight supported or completion of backward propulsion.

| Knee output | Excursion from neutral | Requested speed |
| --- | --- | --- |
| Ordinary flexion / extension | +0.35 / −0.08 rad | 1.5 rad/s |
| Early push | −0.12 rad | 3.0 rad/s |
| Tilt reflex | −0.22 rad | 3.0 rad/s |

These are editable actuator settings in `config.json`, not TNorms or learned
amplitudes. The adapter caps speed at the model's maximum. The body advances
32 ms per native output frame; signed tilt evidence begins at 0.08 rad.

There is **no neural ACK handshake**. Input HTTP requests run separately from
motor delivery; the newest unsent tilt/contact/reward capture replaces older unsent
captures. WALK/REST confirmation is observed without pausing body steps. Every
native motor frame is retained. The isolated ACK populations remain dormant.
This contact design changes the input/output contract and **requires a rebuild**.
Existing motor calibration and the independent tilt-reflex paths are preserved.

Automatic fall recovery is still enabled. It requests STOP, restores the robot
and requests START after settling. Removing ACK does not disable that separate
source of apparent restarts. See [recovery](docs/RECOVERY.md).

There are **551 neurons**, including **77 external neurons across twelve named
inputs**. Each leg's reflex remains **24 high-gamma T5 neurons**, directly
exciting its fast output and its **24-neuron regular extension Beta T5**. The
two reflex connections and the regular support phase drive → knee extension
Beta connections are static. Only four inhibitory release-feedback paths use
STDP3/LTP. Swing inhibition acts at the regular extension
output so it does not prevent that Beta from receiving reflex evidence.

The reward path is 10 outcome input neurons → 10 high-gamma T10 neurons →
17 dopaminergic T3 neurons. Positive reward means new upright forward progress;
zero means no reward. The four new contact inputs each contain four neurons.
Python transmits measurements; it supplies no phase, gait or handoff decision.

## What you learn

- Capture a brief command and retain WALK or REST inside the brain.
- Start an early push while the existing motor pathway builds activity.
- Clear that push from retained neural readiness, without a host timer.
- Start final extension directly from the return pathway, while clearing flexion.
- Combine a return command with measured foot contact inside the brain.
- Retain that confirmation and clear it before the next local movement.
- Recruit the diagonal rear partner after front contact is confirmed.
- Keep local reflexes independent and give them a neural reset long enough to
  avoid the immediate output-clearing loop.
- Recruit regular Beta through a fixed reflex connection while limiting STDP3/LTP
  to four inhibitory release-feedback paths.

Read [goals and interactions](docs/GOALS.md), [the design](docs/DESIGN.md),
[foot-contact feedback](docs/CONTACT.md), [push before swing](docs/PUSH.md),
and [the reflex path](docs/REFLEX.md).

## Requirements

- Linux, Git and Python 3.11 or newer.
- **Webots R2025a installed separately. This package never installs Webots.**
- Prima-Lux, its developer API key and a reachable device address.
- Device Manager 0.6.17 with the compatible 0.4.11 builder on Prima-Lux for
  SDK 0.4.2 reward-type support.
- Internet access to install Python dependencies.

`install.sh` creates or repairs `.venv`, installs SDK 0.4.2 and creates `.env`
if absent. It can install missing Ubuntu Python prerequisites using sudo.
Spot PROTOs, meshes and textures are bundled with relative URLs; Run does not
fetch models or depend on a Webots sample-directory layout.
See [requirements](docs/REQUIREMENTS.md).

## Clone and install

```bash
git clone /absolute/path/to/the-downloaded-touch.bundle primalux-spot-touch
cd primalux-spot-touch
bash install.sh
source .venv/bin/activate
```

Replace `/absolute/path/to/the-downloaded-touch.bundle` with the exact path
provided with the download. After publication, use the repository URL in place
of the bundle path. Edit `.env`:

```dotenv
AB_DEVICE_URL=http://prima-lux.local:8080
AB_DEVICE_API_KEY=YOUR_DEVICE_DEVELOPER_API_KEY
AB_TELEMETRY=true
WEBOTS_EXECUTABLE=/absolute/path/to/webots
```

`WEBOTS_EXECUTABLE` names the executable file, not its containing folder.
Keep `.env` out of Git. For an existing checkout, stop the application with Q,
then fetch the bundle and merge its main branch using `--ff-only`.
Rebuild this inhibitory LTP design even if the previous touch version is installed.
Changing learning rules in a local file does not update the installed brain.
A new build is a new learning condition; do not assume old learned weights transfer.

## Inspect the design

```bash
ab design --brain brain.abdesign.json --env .env
```

Follow START → START_REQUEST → WALK_ENABLED, then PHASE_A_REQUEST → PHASE_A_OUT.
OUT and DRIVE_HG retain each macro state. Inspect LEG_FR_MOVE_HG: it excites the
ordinary motor Betas and PUSH_HG in parallel. Follow hip Beta → SWING_READY →
SWING_READY_HG back to clear the push branch. Then follow KNEE_POS → RETURN_BETA
→ DONE → DONE_HG. Inspect FOOT_FR_CONTACT_HG inhibiting LEG_FR_CONTACT_VETO_HG.
That veto suppresses LEG_FR_CONTACT_MATCH_HG, whose positive drive is DONE_HG.
The resulting CONTACT_READY loop feeds front HANDOFF_BETA → rear MOVE_HG, or
rear MOTOR_FEEDBACK_HG for the phase handoff. Python does not compute these states.

Inspect the direct RETURN_BETA → KNEE_NEG and DONE_HG → KNEE_NEG edges. Both
sources clear KNEE_POS and its extension-output veto at strength 64. The final
extension command starts through these fixed paths while the regular support
Beta is still being recruited; no additional population or input is needed.

Each REFLEX_HG T5 connects directly to KNEE_REFLEX_EXTEND and to the existing
regular KNEE_NEG_BETA T5 through fixed connections. The support phase drive →
KNEE_NEG_BETA edges are fixed too. Inspect STDP3/LTP only on each phase's
RELEASE → FEEDBACK_BETA and RELEASE → BETA inhibitory edges.
Follow the fast output through two Beta
T3 recovery stages back to clear itself. ACTIVE is diagnostic only.

Close the Designer with Ctrl+C before continuing. If you edit on the Canvas,
save/download `brain.abdesign.json` before Build. Install and Run never
regenerate your design.

## Build the brain

Stop a currently running device brain before installing the design:

```bash
ab device --env .env stop
```

```bash
ab build brain --brain brain.abdesign.json --env .env
```

Wait for READY. Run uses the installed brain and does not build it.

## Run the switch with reward disabled

```bash
ab run -ab --env .env walk
```

Focus the Webots 3D view: **W** starts, **S** stops stepping, **R** requests
simulator recovery, and **Q** stops and saves. Closing Webots also stops and
saves the SDK session. The reflex is enabled in walk mode; only reward is zero.
There is no maximum run duration or automatic elapsed-time cutoff.

Inspect both the phase readouts and the actual hip/knee outputs. A phase being
active is not evidence that the feet are planted. Neural propagation introduces
transition steps; the adapter does not hide them with a motor timer.

The world has a large marked floor and a wider tracking view. Automatic recovery
is explicit simulator assistance, not learned balance or self-righting.

## Enable learning after checking the static behavior

Stop with Q and wait for saving, then run:

```bash
ab run -ab --env .env learn
```

One physical reward signal may adjust **four STDP3/LTP inhibitory returns**:
each phase's RELEASE → FEEDBACK_BETA and RELEASE → BETA. These are the only
plastic connections. All excitatory paths, including support phase drive →
regular knee extension Beta, stay fixed. Contact, reflex, state interlocks,
motor vetoes, command paths and all other reset connections also stay fixed.
Reflex activity still recruits both fast extension and the normal Beta, but
neither branch learns. Learning can alter release recovery; it is not a
substitute for working coordination.

**All four plastic connections are inhibitory and use LTP. No connection uses LTD.** LTP follows
signed eligibility; it does not promise that every update strengthens the
connection. Every contact and reflex connection remains static. Inspect the
selected edges in the Designer and rebuild before running.

For a design with no learning metadata, author it explicitly, then inspect and
build it with the same SDK commands:

```bash
python design_brain.py --static
```

`python design_brain.py` restores the supplied learning-enabled design. Neither
command is an installer or launcher. See [design](docs/DESIGN.md) and
[control and reward](docs/CONTROL.md).

The startup line prints four push outputs, four fast reflex outputs, 10 reward input neurons,
four foot sensors with four neurons each, the design hash and the project folder. `logs/run-*/settings.json` records them
too. This identifies which local package actually ran.
`neuron-telemetry.jsonl` now records actual internal neuron activity automatically,
including the reflex, normal Beta, phase-feedback and reward populations. The
recorder reads the existing SDK viewer stream and never controls movement.

## Checks and limits

Construction uses 551/10,000 neurons and 297,444 bytes of connection matrices;
other prepared-image data also consumes memory. Application tests cover actual
SDK encoding, sensor validation, asynchronous publication, motor delivery and
Stop/save. Local native-cell checks exercise missing, delayed and intermittent
contact with static weights. These are not a Webots physics or Prima-Lux device
run. Physical walking and learning still need your test. See
[validation](docs/VALIDATION.md).

`contact-inputs.jsonl` records accepted contact publications. Each observation
also records raw `foot_contact`, encoded `contact_inputs` and neural outputs.
The periodic console line shows `contacts` and `contact_ready`. Compare all three
before attributing a stalled handoff to learning.

## License

Project code: [Artificial Brains Example Code License](LICENSE). Bundled Webots assets retain
their upstream terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
