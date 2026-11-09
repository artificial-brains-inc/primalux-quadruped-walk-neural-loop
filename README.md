# Spot: a neural walking switch and local support reflexes

A developer teaching example for Prima-Lux and Webots. Each leg first gives a
small extension push, then flexes and advances, then returns to support. Neural
activity sequences the movements; independent tilt reflexes can override a
leg's knee motion.

| Macro state | First | Then |
| --- | --- | --- |
| A | Front-right push → swing → return | Rear-left push → swing → return |
| B | Front-left push → swing → return | Rear-right push → swing → return |

The return pathway directly activates final knee extension and clears flexion.
It also recruits the rear movement through its existing handoff Beta, so final
extension can start before the next leg's initial push. A front swing
command does not start the rear swing. The sequence is intended to prepare
support before a leg lifts; these neural events do not measure actual unloading
or foot contact.

| Knee output | Excursion from neutral | Requested speed |
| --- | --- | --- |
| Ordinary flexion / extension | +0.35 / −0.08 rad | 1.5 rad/s |
| Early push | −0.12 rad | 3.0 rad/s |
| Tilt reflex | −0.22 rad | 3.0 rad/s |

These are editable actuator settings in `config.json`, not TNorms or learned
amplitudes. The adapter caps speed at the model's maximum. The body advances
32 ms per native output frame; signed tilt evidence begins at 0.08 rad.

There is **no neural ACK handshake**. Input HTTP requests run separately from
motor delivery; the newest unsent tilt/reward capture replaces older unsent
captures. WALK/REST confirmation is observed without pausing body steps. Every
native motor frame is retained. The graph, TNorms and motor settings are unchanged;
its isolated ACK populations remain dormant for installed-brain compatibility.

Automatic fall recovery is still enabled. It requests STOP, restores the robot
and requests START after settling. Removing ACK does not disable that separate
source of apparent restarts. See [recovery](docs/RECOVERY.md).

There are **503 neurons**, including **61 external neurons across eight named
inputs**. Each leg's reflex remains **24 high-gamma T5 neurons**, directly
exciting its fast output and its **24-neuron regular extension Beta T5**. The
two reflex connections are static. STDP3/LTP is on the regular support phase
drive → knee extension Beta connection, one per leg. Swing inhibition acts at the regular extension
output so it does not prevent that Beta from receiving reflex evidence.

The reward path is 10 outcome input neurons → 10 high-gamma T10 neurons →
17 dopaminergic T3 neurons. Positive reward means new upright forward progress;
zero means no reward. No new external gait, phase or progress inputs are added.

## What you learn

- Capture a brief command and retain WALK or REST inside the brain.
- Start an early push while the existing motor pathway builds activity.
- Clear that push from retained neural readiness, without a host timer.
- Start final extension directly from the return pathway, while clearing flexion.
- Return a front leg to support before recruiting its diagonal rear partner.
- Keep local reflexes independent and give them a neural reset long enough to
  avoid the immediate output-clearing loop.
- Recruit regular Beta through a fixed reflex connection, with STDP3 on its
  normal support input.

Read [goals and interactions](docs/GOALS.md), [the design](docs/DESIGN.md),
[push before swing](docs/PUSH.md), and [the reflex path](docs/REFLEX.md).

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
git clone "$HOME/Downloads/primalux-spot-no-ack.bundle" primalux-spot-switch
cd primalux-spot-switch
bash install.sh
source .venv/bin/activate
```

After publication, use the repository URL in place of the bundle path. Edit `.env`:

```dotenv
AB_DEVICE_URL=http://prima-lux.local:8080
AB_DEVICE_API_KEY=YOUR_DEVICE_DEVELOPER_API_KEY
AB_TELEMETRY=true
WEBOTS_EXECUTABLE=/absolute/path/to/webots
```

`WEBOTS_EXECUTABLE` names the executable file, not its containing folder.
Keep `.env` out of Git. For an existing checkout, stop the application with Q,
then fetch the bundle and merge its main branch using `--ff-only`.
If the previous continuous-run design is already installed, this adapter update
requires no brain rebuild. The following design/build steps are for a new install.

## Inspect the design

```bash
ab design --brain brain.abdesign.json --env .env
```

Follow START → START_REQUEST → WALK_ENABLED, then PHASE_A_REQUEST → PHASE_A_OUT.
OUT and DRIVE_HG retain each macro state. Inspect LEG_FR_MOVE_HG: it excites the
ordinary motor Betas and PUSH_HG in parallel. Follow hip Beta → SWING_READY →
SWING_READY_HG back to clear the push branch. Then follow KNEE_POS → RETURN_BETA
→ DONE → DONE_HG. Front DONE feeds HANDOFF_BETA → rear MOVE_HG; rear DONE feeds
the macro handoff pathway. Python does not republish these internal signals.

Inspect the direct RETURN_BETA → KNEE_NEG and DONE_HG → KNEE_NEG edges. Both
sources clear KNEE_POS and its extension-output veto at strength 64. The final
extension command starts through these fixed paths while the regular support
Beta is still being recruited; no additional population or input is needed.

Each REFLEX_HG T5 connects directly to KNEE_REFLEX_EXTEND and to the existing
regular KNEE_NEG_BETA T5 through fixed connections. Inspect STDP3 on each
PHASE_support_DRIVE_HG → KNEE_NEG_BETA edge. Follow the fast output through two Beta
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

One physical reward signal may adjust **four STDP3/LTD inhibitory returns** from
RELEASE to its own FEEDBACK_BETA and BETA, plus **four excitatory STDP3/LTP edges**
from each leg's support phase drive to its regular knee extension Beta. All
reflex connections, local DONE → Beta, Beta → output, state interlocks, motor
vetoes, command paths and resets remain static. Reflex activity can recruit the
postsynaptic Beta while the regular presynaptic drive is active, contributing to
eligibility on that regular connection. Learning can alter release recovery and
normal support recruitment; it is not
a substitute for working coordination.

This LTD experiment changes the reward direction only on the four RELEASE
feedback connections. LTP follows signed eligibility; LTD reverses it. LTD does
not guarantee weaker inhibition or more overlap. The regular support inputs
retain LTP, and every reflex connection remains static. Inspect the selected
edges in the Designer and rebuild before running; changing files does not change
the brain already installed on the device.

For a design with no learning metadata, author it explicitly, then inspect and
build it with the same SDK commands:

```bash
python design_brain.py --static
```

`python design_brain.py` restores the supplied learning-enabled design. Neither
command is an installer or launcher. See [design](docs/DESIGN.md) and
[control and reward](docs/CONTROL.md).

The startup line prints four push outputs, four fast reflex outputs, 10 reward input neurons,
the design hash and the project folder. `logs/run-*/settings.json` records them
too. This identifies which local package actually ran.
`neuron-telemetry.jsonl` now records actual internal neuron activity automatically,
including the reflex, normal Beta, phase-feedback and reward populations. The
recorder reads the existing SDK viewer stream and never controls movement.

## Checks and limits

Construction uses 503/10,000 neurons and 292,796 bytes of connection matrices;
other prepared-image data also consumes memory. The local complete-circuit check
uses single START/STOP events, internal motor feedback and injected tilt evidence.
It checks push/swing order, final extension timing, front support before rear
push and swing, reflex recruitment,
clearing, stopping and restarting. It includes
transition gaps and is not an FPGA or Webots run. Physical balance and learned
walking still need your device test. See [validation](docs/VALIDATION.md).

## License

Project code: [Artificial Brains Example Code License](LICENSE). Bundled Webots assets retain
their upstream terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
