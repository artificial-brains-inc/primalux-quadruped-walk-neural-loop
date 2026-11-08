# Spot: a neural walking switch and local support reflexes

A developer teaching example for Prima-Lux and Webots. One neural switch holds
one of two complementary motor patterns. Motor activity recruits the handoff to
the other pattern. Independent support reflexes can override a leg's knee motion.

| Switch state | Front-left + rear-right | Front-right + rear-left |
| --- | --- | --- |
| A | Small extension; support and backward hip movement | Larger flexion and forward hip movement |
| B | Larger flexion and forward hip movement | Small extension; support and backward hip movement |

Knee targets are **−0.08 rad for extension and +0.35 rad for flexion**, relative
to neutral. Hip targets are ±0.20 rad. These are actuator calibration values,
not TNorms or learned amplitudes. A separate reflex motor output requests
**−0.22 rad at up to 3.0 rad/s**; ordinary knee motion uses 1.5 rad/s. The
reflex also excites the normal extension Beta through a learning connection.
These actuator calibration values remain editable in `config.json`.

There are **461 neurons**, including **61 external neurons across eight named
inputs**. Four leg groups contain 24 opposing gait Betas. Each leg also has a
24-neuron high-gamma T5 reflex that directly drives its fast extension output.
The same high-gamma directly excites the regular extension Beta through STDP3.
Four rear gait relays make RR follow FL and RL follow FR through their neural hip outputs.
The reward path contains 10 outcome input neurons, 10 high-gamma T10 relay
neurons and 17 dopaminergic T3 neurons. It classifies positive reward as new
upright forward progress; zero is no reward. No additional external phase,
progress or motor-feedback inputs are used.

Python acquires and encodes measurements, applies local neural motor outputs and
publishes physical reward. The switch, handoff, reflex selection and reset live
in the graph. Webots position servos track the commanded joint angles.

## What you learn

- Capture a brief command and retain a walking goal inside the brain.
- Build a two-state switch whose states select complementary motor populations.
- Feed actual motor output neurons back into a neural handoff pathway.
- Let a local reflex excite extension and inhibit flexion without selecting a
  phase in the controller or suppressing another leg.
- Connect reflex high-gamma directly to regular extension Beta, creating a path
  for STDP3 eligibility; keep the fast reflex output on its fixed direct branch.

Read [goals and interactions](docs/GOALS.md), [the design](docs/DESIGN.md), and
[the reflex path](docs/REFLEX.md).

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
git clone "$HOME/Downloads/primalux-spot-direct-hg5-rear-relay.bundle" primalux-spot-switch
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

## Inspect the design

```bash
ab design --brain brain.abdesign.json --env .env
```

Follow START → START_REQUEST → WALK_ENABLED, then PHASE_A_REQUEST → PHASE_A_OUT.
OUT and DRIVE_HG retain each switch state. Follow the four hip output neurons
back to MOTOR_FEEDBACK_HG → FEEDBACK_BETA → BETA → RELEASE → the other request.
These are internal connections; Python does not republish their activity.

Below the switch, inspect the four leg motor groups. Each REFLEX_HG T5 has a
fixed direct edge to KNEE_REFLEX_EXTEND and a direct STDP3 edge to the regular
KNEE_NEG_BETA T5. That Beta also receives its normal gait source. Inspect both
operand edges at one unit each. ACTIVE is only a diagnostic; it does not command
a motor. Rear gait relays follow the diagonal front hip outputs.

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

One physical reward signal may adjust **four STDP3/LTP inhibitory returns** from
RELEASE to its own FEEDBACK_BETA and BETA, plus **four excitatory STDP3/LTP edges**
from each REFLEX_HG to its regular knee extension Beta. State interlocks, motor
vetoes, command paths, the fast reflex branch and resets remain static. Learning
can alter release recovery and reflex recruitment of normal extension; it is not
a substitute for working coordination.

For a design with no learning metadata, author it explicitly, then inspect and
build it with the same SDK commands:

```bash
python design_brain.py --static
```

`python design_brain.py` restores the supplied learning-enabled design. Neither
command is an installer or launcher. See [design](docs/DESIGN.md) and
[control and reward](docs/CONTROL.md).

The startup line prints four fast reflex motor outputs, 10 reward input neurons,
the design hash and the project folder. `logs/run-*/settings.json` records them
too. This identifies which local package actually ran.
`neuron-telemetry.jsonl` now records actual internal neuron activity automatically,
including the reflex, normal Beta, phase-feedback and reward populations. The
recorder reads the existing SDK viewer stream and never controls movement.

## Checks and limits

Construction uses 461/10,000 neurons and 305,284 bytes of connection matrices;
other prepared-image data also consumes memory. The local complete-circuit check
uses single START/STOP events, internal motor feedback and injected tilt evidence.
It checks alternation, local overrides, stopping and restarting. It includes
transition gaps and is not an FPGA or Webots run. Physical balance and learned
walking still need your device test. See [validation](docs/VALIDATION.md).

## License

Project code: [Artificial Brains Example Code License](LICENSE). Bundled Webots assets retain
their upstream terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
