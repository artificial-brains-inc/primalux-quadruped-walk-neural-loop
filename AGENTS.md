# Editing this example

Build behavior through the public SDK and the current Artificial Brains guide.
Keep private construction code, formulas, compiled images and credentials out.

- Eight external input populations, 61 neurons: START, STOP and ACK have one
  neuron each; reward has 10; four signed tilt populations have 12 each.
- Reward class is positive outcome for upright forward progress. Ten outcome
  input neurons feed 10 high-gamma T10 relay neurons and 17 dopaminergic T3
  neurons in the compatible build. Zero means no reward, not punishment.
  Use publish_reward magnitude 1 for all 10 input neurons; never magnitude 10.
- A supports FL/RR and swings FR/RL. B supports FR/RL and swings FL/RR.
  These are diagonal groups, not the robot's left and right sides.
- Each switch state is retained through OUT → DRIVE_HG → OUT. Its request
  persists through REQUEST → REQUEST_HG → REQUEST until the state takes over.
- START captures A once. Four appropriate hip output neurons feed each phase's
  MOTOR_FEEDBACK_HG → FEEDBACK_BETA T5 → BETA T5 → RELEASE T3.
  RELEASE captures the opposite request. No Python clock or progress input.
- Requests clear the opposite state and feedback path. State relays oppose the
  other state and feedback relay. Keep these interlocks static at strength 4.
  Successful state recruitment clears its own request/helper at strength 64.
- STDP3/LTP belongs to four RELEASE returns to the same phase's
  FEEDBACK_BETA and BETA (initial strength 4), plus four REFLEX_HG
  excitatory connections into the normal knee extension Betas. Other edges are static.
  Start validation in walk mode with reward zero. Do not claim learned walking.
- Keep 24 local gait Betas. Front Betas receive the shared phase drive. Each
  rear leg has two one-neuron high-gamma T10 relays, driven by the diagonal
  front partner's appropriate HIP output: RR follows FL, RL follows FR.
  Rear Betas receive those relays. No Python delay; reflexes bypass the relays.
- Each reflex trigger is high-gamma T5, 24 neurons, directly exciting that
  leg's KNEE_REFLEX_EXTEND output. There is no dedicated reflex motor Beta.
- Reflex HG also directly excites the regular knee extension Beta T5 through
  STDP3/LTP. Both this edge and its gait-drive edge have role operand, units 1:
  the initial Beta T5 OR construction accepts either source. There is no
  output-derived teaching relay. Normal extension Betas have 24 neurons;
  other gait Betas have 2. Learning deliberately changes reflex recruitment.
- Fast output also recruits OUTPUT_RESET_HG T10 (1 neuron). At strength 4 it
  clears the fast output and ACTIVE, and inhibits its own reflex trigger.
  Thus reset follows actual fast output activation, not an earlier Beta stage.
- Reflex HG inhibits its own flexion Beta/output and local extension-veto relay
  at strength 64. The local relay vetoes normal extension Beta/output only.
  Never inhibit another leg or a shared phase. ACTIVE is diagnostic only.
- The reflex has local excitatory feedback. No guard, corner veto or host timer.
- Output neurons are bistable and require explicit clearing. Do not alter SDK
  output semantics, delay motor commands in Python, or infer commands from phases.
- Python reads sensors, encodes signed tilt, publishes physical reward, applies
  local motor outputs and enforces actuator limits. It does not choose a leg,
  gait phase, corrective target, trajectory, IK solution or handoff time.
- Reflex and switch feedback are neural activity, not proof of foot contact or
  completed movement. The adapter's position servos perform low-level tracking.
- Preserve event-based START/STOP capture, transport ACK, and goal confirmation.
  ACK is not WALK/REST confirmation. Never add periodic command resends.
- Preserve Q/close Stop/save and explicit simulator recovery. Recovery is a
  supervisor reset, not learned self-righting. Never reward a reset displacement.
- Installer never installs Webots or regenerates the design. Keep clone, install,
  design, build and run as separate SDK steps. Use SDK 0.4.2.
- Construction, mocked SDK tests and the local native-cell check do not prove
  device equivalence, physical balance, successful walking or learning.

Record internal firing through the read-only neuron telemetry stream. Recording
errors must be visible and must not choose actions or retime the motor loop.
