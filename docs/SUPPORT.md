# Preparing the next step

The cycle remains FR → RL → FL → RR → FR. The current leg’s return starts the
next grounded preparation. Qualified landing then releases the next swing.
There is no new input, host timer, phase selector or ACK wait.

## Neural paths

- LEG_current_RETURN_BETA → STEP_next_PREPARE_HG → LEG_next_PUSH_HG → next KNEE_PUSH.
- PREPARE_HG also directly excites fixed HIP/ABD support outputs, selected by the
  direction table below. PREPARE is retained with an output-to-OPU feedback loop.
- The next support plan clears the previous plan. Opposing support directions
  clear their antagonist outputs at strength 64; outputs cannot just go silent
  upstream because they are bistable.
- Each leg’s ACTIVE_HG inhibits its own support outputs at strength 64. The other
  legs receive the posture adjustment. During preparation the upcoming leg is
  still in STANCE, so it can push and participate before lifting.
- The kick output recruits its own termination and retains KICK_DONE. Hip
  SWING_READY cannot clear a pending kick. DONE
  also clears it. STOP/REST clears the plans and all new motor outputs.

PREPARE denotes a retained support plan, including its own subsequent swing.
It does not prove that the body has transferred its weight. Contact still gates
HANDOFF_BETA and next REQUEST; an absent landing cannot start the next swing.

## Fixed support calibration

| Foot about to lift | Intended body shift | HIP support output | ABD support output |
| --- | --- | --- | --- |
| Front right | Back and left | POS | POS |
| Rear left | Forward and right | NEG | NEG |
| Front left | Back and right | POS | NEG |
| Rear right | Forward and left | NEG | POS |

This table is wiring in the brain. The controller sees only individual motor
outputs; it does not calculate a shift direction or decide which leg supports.
A POS minus NEG support output adds a fixed offset to that joint’s ordinary
target: HIP 0.04 rad, ABD 0.05 rad. Opposing support outputs cancel. These offsets
use the existing joint speed limits. Knee stroke amplitudes and reflex settings
are unchanged. Combined endpoints are checked against the model’s joint limits.

The sign check uses the bundled SpotLeg geometry and joint axes. Near the
standing support pose, increasing HIP moves the foot forward relative to the
body; increasing ABD moves it right on both left and right legs. With a planted
foot, the corresponding body displacement is opposite. This is a kinematic sign
check, not a force, center-of-mass or stability calculation. No IK runs in the
controller. The chosen small offsets are provisional physical calibration.

The four bumper sensors still report touch, not load. Existing signed tilt
reflexes remain independent and static. They can respond to tilt but do not
verify that a planned support adjustment succeeded.

## Inspect the result

Watch `support_plan`, `push_motors`, `active_legs` and `contacts` in the console.
Use observations for frame-level timing: console snapshots are only every 30
frames. `next_push_before_previous_touchdown_frames` reports actual early push
outputs while the previous active foot is measured airborne. A zero count can
mean late preparation or a very short/missed airborne interval; inspect the raw
contact and neuron traces before drawing a conclusion.

The current fixture checks use synthetic contact and native cell updates. They
verify ordering, clearing and motor-output overlap, not physical weight transfer.
First test the static design on your device, comparing body pitch/roll, falls,
forward progress and contact timing. Keep the learning design for the later
comparison. Four BRAKE → HANDOFF and four CONTACT_READY_HG → LOOP_HG
inhibitory STDP3/LTP paths learn. Support and reflex connections remain static.
For a controlled posture-offset comparison, set both `support_shift` offsets in
config.json to zero; no brain rebuild is needed for that calibration-only change.
