# Editing this example

Build through SDK 0.4.2 public fields and the current Artificial Brains guide.
Keep proprietary construction code, equations, compiled images and credentials out.

- Twelve external populations, 77 neurons: START/STOP/ACK each 1, reward 10,
  four signed tilt populations each 12, four measured foot contacts each 4.
  No controller-derived phase, gait or handoff inputs.
- A runs FR then RL; B runs FL then RR. These are ordered diagonal sequences,
  not simultaneous diagonal swings. WALK/REST and A/B retain their neural states.
- Each leg's MOVE_HG drives its motor Betas and an early PUSH_HG branch.
  PUSH_HG directly excites KNEE_PUSH and inhibits local knee flexion output.
  KNEE_PUSH returns feedback to PUSH_HG. Hip Beta recruits SWING_READY, retained
  through its HG helper, which clears PUSH_HG and KNEE_PUSH at strength 64.
  Readiness must not be inhibited by its own push branch.
- Actual KNEE_POS output recruits RETURN_BETA T3, then retained DONE/DONE_HG.
  RETURN_BETA directly excites KNEE_NEG and inhibits KNEE_POS/output veto at 64.
  DONE_HG retains the same direct extension and clearing paths. Do not put an
  extra Beta stage between the return signal and the final extension output.
  DONE also ends this leg's movement and recruits its support Betas, except rear
  hip retraction. Rear HIP_NEG_BETA receives only its support phase. Rear DONE
  clears HIP_POS_BETA but leaves HIP_POS latched through landing; support phase,
  antagonistic Beta and REST clear that output. Do not return the rear hip to
  neutral early by clearing HIP_POS at DONE. Front
  CONTACT_READY_HG recruits HANDOFF_BETA T3, which starts diagonal rear MOVE_HG.
  Do not trigger rear movement from a front swing or reflex motor output.
- Rear CONTACT_READY_HG directly recruits FEEDBACK_BETA T5, which requests the
  opposite phase. Do not put MOTOR_FEEDBACK_HG or the later BETA/RELEASE stages
  between this feedback and the phase request. FEEDBACK_BETA → BETA → RELEASE
  runs as a reset branch, with four plastic inhibitory returns. Opposite phase
  requests clear the old OUT/DRIVE, not that reset branch; let it finish.
- Rear hip support and same-side front MOVE share a phase. Do not add a rear
  motor-output → front motor-output shortcut. Contact changes the switch, and
  the switch recruits the ordinary motor pathways.
- Foot contact input 4 → sensory HG T10 4 → CONTACT_MATCH_HG T10 4 is the
  positive contact path. Raw contact also drives RETURN_VETO_HG T10 4, which
  inhibits MATCH at 64. DONE_HG inhibits RETURN_VETO_HG at 64, permitting contact
  during return. DONE is permission, not a substitute source of contact.
  MATCH recruits CONTACT_READY; READY/output-HG retains the event. MOVE,
  support phase and STOP/REST clear MATCH/READY/HG at 64. Do not clear the
  sensory RETURN_VETO in REST: it must block unarmed contact across START.
  All these edges are static. Contact is pad collision, not load or completed
  push. No prior airborne transition is required. Contact does not block landing.
- Each reflex is 24 high-gamma T5 neurons directly exciting a fast motor output
  and its existing regular extension Beta T5 through fixed connections. Keep both
  edges static. All excitatory connections, including support phase drive →
  regular Beta, local DONE → Beta and Beta → output, must remain static.
- Normal extension Beta receives gait support, local DONE and reflex evidence
  as one canonical operand unit each. Swing veto acts at its output, not inside
  that Beta. Knee opposition uses state/output vetoes; do not starve the Beta
  with continuous swing inhibition. Reflex still inhibits flexion Beta/output.
- SWING_READY_HG drives local EXTENSION_VETO_HG T10. It vetoes normal extension
  output at strength 64. Reflex HG suppresses that same veto and local flexion
  Beta/output at strength 64. Never inhibit another leg or a shared phase.
- Fast output recruits RECOVERY_BETA T3 (2 neurons), then OUTPUT_RESET_BETA T3
  (4 neurons). The latter clears fast output/ACTIVE and inhibits its own HG
  trigger at strength 4. Do not restore the immediate one-HG reset that cut the
  observed pulse after two frames. No reflex guard or controller burst timer.
- ACTIVE is diagnostic only. All outputs are bistable and have explicit clearing.
  STOP/REST clears all movement, push, reflex, readiness, return and phase paths.
- Learning uses STDP3/LTP only on the four release inhibitory returns to each
  phase's FEEDBACK_BETA and BETA. Every other edge is static, including other
  inhibitory paths. No connection uses LTD. LTP follows signed eligibility, so it does not
  guarantee every update strengthens a connection.
  Reward is positive upright forward progress: 10 input
  → 10 HG T10 → 17 dopaminergic T3 neurons. Zero is no reward, not punishment.
  Do not claim that wiring alone proves eligibility, weight changes or learning.
- Python senses/encodes, publishes reward, decodes local outputs and applies
  actuator limits. No IK, phase choice, target-completion wait or min-stroke hold.
  Same-direction extension outputs use the largest configured excursion, not
  summed angles. Opposing commands cancel. Body step is 32 ms, threshold 0.08 rad.
- No neural ACK handshake: clear the legacy ACK input at startup, never stimulate
  it or wait for its readout. Keep dormant ACK populations isolated. Observe WALK/REST without consuming or withholding motor
  frames. Publish inputs on a separate worker; one latest unsent feedback capture
  replaces older unsent captures. Do not queue stale sensor history or replay it.
- Preserve event command capture, Q/close Stop/save and explicit simulator
  recovery. Never resend commands periodically. Supervisor recovery sends
  STOP/START and changes neural activity; it is not neural self-righting.
- Runs have no elapsed-time cutoff. The user decides when to stop; do not add
  a maximum duration or replace it with a large finite limit.
- Installer never installs Webots or regenerates the design. Keep install,
  design, build and run as separate SDK steps. Preserve the project license.
- Local construction, mocked SDK tests and native-cell harnesses do not validate
  device equivalence, physical weight transfer, stability or learned walking.
- Foot-pad TouchSensors must have a positive-mass Physics body. A kinematic
  child bumper can report overlap but cannot supply ground reaction to the leg.
  Keep the original pad pose/shape and no duplicate parent pad collider.
- Record internal neuron activity through the read-only stream, including zeros
  and visible recording errors. The observer must not control or pace movement.
