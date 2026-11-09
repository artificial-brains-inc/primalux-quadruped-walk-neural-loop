# Editing this example

Use SDK 0.4.2 public design fields and the compatible Artificial Brains guide.
Keep proprietary construction code, formulas, compiled images and credentials out.

- FR → RL → FL → RR → FR is a four-stage cascade. START seeds FR once;
  STOP/REST clears it. The controller never selects stages or generates a gait.
- Preserve each local push/swing/return primitive, its regular motor Betas and stroke calibration.
  PREPARE adds a two-neuron HG T10 input to the push relay (3 front / 4 rear).
  Previous RETURN recruits next PREPARE before landing. START seeds FR PREPARE.
  PREPARE retains the support plan through its own swing; next PREPARE clears it.
  Each leg has a recurrent LOOP_HG driving MOVE_HG. Only CONTACT_READY_HG
  inhibits this recurrence during WALK; its STDP3/LTP feedback starts at 16.
  STOP/REST remain global overrides. Motor outputs, DONE, retry and STANCE
  must never inhibit LOOP_HG. Initial planted contact cannot terminate it:
  qualifying landing requires AIR_SEEN and return evidence.
  Preserve CONTACT_READY through STANCE; only a fresh local REQUEST or
  global STOP/REST clears it. The fixed STOP/REST inhibition into LOOP is 64.
  PUSH is a pulse within the leg attempt and is not self-recurrent. Its own
  output terminates the pulse; DONE resets MOVE for return. Two local Beta T3
  stages (2 then 4 neurons) reset phase memories for another attempt if the
  sensor has not stopped the loop. Preserve AIR_SEEN/contact memories across retries.
  FLEX_WAIT_HG blocks knee flexion until the ordinary extension veto is active.
- Sixteen fixed HIP/ABD support outputs add small signed actuator offsets.
  Direction selection and swing exclusion remain neural. ACTIVE_HG vetoes its
  own support outputs; opposing plans clear antagonists. No phase-based decoder.
  Never describe bumper contact or a support-plan output as measured load.
  Rear MOVE input uses local Beta T3. No motor-output-to-motor-output shortcut.
- Landing needs measured contact, AIR_SEEN from lift-off during the active turn,
  and local DONE. Sensor gates are fixed local veto/disinhibition paths.
  Never treat input silence as no contact. Never let planted initial feet pass turns.
- Four physical bumpers have two explicit four-neuron rails each: CONTACT and AIR.
  Python may complement the measured binary value; event memory remains neural.
  Suspend/clear both rails during recovery/shutdown. Do not synthesize AIR then.
- The contact gate drives HANDOFF_BETA T5, opposed by BRAKE_BETA T5 recruited
  from current ACTIVE before landing. Both are two-neuron populations.
  The four BRAKE→HANDOFF and four CONTACT_READY_HG→LOOP_HG inhibitory
  feedback edges use STDP3/LTP. No other path may learn.
  Initial strengths are 0.5 for handoff and 16 for sensor-to-loop inhibition.
  These are provisional settings, not measured physical optima.
- Ship static and learning companions with identical topology/TNorms/strengths.
  The root design and default mode are learning/learn. Static omits learning fields.
  Reject mode/design mismatches before launching Webots; never silently switch graphs.
  All excitatory, reflex, other sensor gating, state interlock and STOP paths stay static.
- Each independent reflex remains high-gamma T5, 24 neurons, driving its fast
  output and regular knee extension Beta T5 (24 neurons). It inhibits local
  knee flexion Beta/output and its extension-output veto. No cross-corner inhibition.
  Two Beta T3 stages (2 then 4 neurons) clear the reflex from its own activity.
- Reward: 10 input → 10 HG T10 → 17 dopaminergic T3. Positive upright forward
  progress is evidence, not a motor command. Do not claim wiring proves learning.
- 93 external neurons /16 populations include command/dormant ACK3, reward10,
  signed tilt48 and foot-state32. Counts are neurons, not physical sensors.
- No neural ACK, periodic START resend, host minimum stroke, gait timer or run cap.
  Motor frames keep advancing the body while input HTTP and goal confirmation run.
  Keep only the latest unsent sensor capture. Report transport errors visibly.
- Preserve Q/Webots-close Stop/save and explicit simulator recovery. Recovery
  sends STOP/START and is assistance, not neural self-righting.
- Every retained output has explicit clearing. Keep sensory vetoes available
  during REST while clearing event memories. Verify restart and missing evidence.
- Preserve positive-mass foot-pad Physics, original collider placement, world,
  cameras, floor markings, bundled assets and project/upstream licenses.
- Install never installs Webots or regenerates the graph. Keep install, design,
  build and run as explicit SDK steps. Do not ship private testing machinery.
- Record raw center of mass, foot-center positions and motor torque as read-only
  diagnostics. These never select a phase, calculate motor commands or enter brain inputs.
- Record read-only internal neuron activity, including zeros and errors, without
  pacing behavior. Compare actual progress, recoveries and contact timing.
- Construction, mocked SDK tests and synthetic-contact native checks do not
  establish physical stability, device equivalence or learned improvement.
