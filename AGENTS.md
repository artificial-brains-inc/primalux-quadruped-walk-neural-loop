# Editing this example

Build through SDK 0.4.2 public fields and the current Artificial Brains guide.
Keep proprietary construction code, equations, compiled images and credentials out.

- Eight external populations, 61 neurons: START/STOP/ACK each 1, reward 10,
  four signed tilt populations each 12. No new phase, gait or progress inputs.
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
  DONE also ends this leg's movement and recruits its normal support Betas. Front
  DONE_HG recruits HANDOFF_BETA T3, which starts the diagonal rear MOVE_HG.
  Do not trigger rear movement from a front swing or reflex motor output.
- Rear DONE_HG recruits its phase's MOTOR_FEEDBACK_HG → FEEDBACK_BETA T5 →
  BETA T5 → RELEASE T3 → opposite request. No host gait period or leg selection.
  Return, readiness and handoff are command history, not measured foot contact.
- Each reflex is 24 high-gamma T5 neurons directly exciting a fast motor output
  and its existing regular extension Beta T5 through STDP3/LTP. Keep both edges.
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
- Learning remains on four release inhibitory returns and four direct reflex
  HG → normal Beta edges. Reward is positive upright forward progress: 10 input
  → 10 HG T10 → 17 dopaminergic T3 neurons. Zero is no reward, not punishment.
  Do not claim that wiring alone proves eligibility, weight changes or learning.
- Python senses/encodes, publishes reward, decodes local outputs and applies
  actuator limits. No IK, phase choice, target-completion wait or min-stroke hold.
  Same-direction extension outputs use the largest configured excursion, not
  summed angles. Opposing commands cancel. Body step is 32 ms, threshold 0.08 rad.
- Preserve event command capture, transport ACK, separate goal confirmation,
  Q/close Stop/save and explicit simulator recovery. Never resend commands
  periodically. Supervisor recovery is not neural self-righting.
- Installer never installs Webots or regenerates the design. Keep install,
  design, build and run as separate SDK steps. Preserve the project license.
- Local construction, mocked SDK tests and native-cell harnesses do not validate
  device equivalence, physical weight transfer, stability or learned walking.
- Record internal neuron activity through the read-only stream, including zeros
  and visible recording errors. The observer must not control or pace movement.
