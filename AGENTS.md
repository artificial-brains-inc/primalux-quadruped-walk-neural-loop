# Editing this example

Build behavior through the public SDK and the current Artificial Brains guide.
Keep private construction code, formulas, compiled images and credentials out.

- Eight external input populations, 52 neurons: START, STOP, ACK and reward
  have one neuron each; four signed tilt populations have 12 each.
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
- STDP3/LTP belongs only to the four RELEASE returns to the same phase's
  FEEDBACK_BETA and BETA, initially strength 4. All other connections are static.
  Start validation in walk mode with reward zero. Do not claim learned walking.
- Keep 24 local gait Betas and four additional reflex extension Betas. A state
  relay excites each appropriate gait Beta; the opposite state vetoes its Beta
  and output. Each local motor Beta opposes its antagonist and output.
- Each reflex is high-gamma T3, 24 neurons. Its separate extension Beta T5 has
  24 neurons and drives that leg's existing knee extension output. Its Beta
  recruits a high-gamma T3 reset (24 neurons) that inhibits its own reflex.
- Reflex HG inhibits its own flexion Beta/output and local extension-veto relay
  at strength 64. That relay normally carries the swing phase's veto to both
  extension Betas and their output. Never inhibit another leg or shared phase.
- The reflex has local excitatory feedback. ACTIVE is diagnostic only and has
  no outgoing connection. No guard, corner veto or controller-side reflex timer.
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
