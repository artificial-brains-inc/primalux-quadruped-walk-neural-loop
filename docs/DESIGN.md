# One switch, two complementary patterns

A and B are the two retained states of one neural switch. A supports FL/RR while
FR/RL flex and advance. B exchanges those roles. Each joint has opposing local
Beta T5 populations and explicit output-clearing paths. No controller-side phase
selector, gait clock, trajectory or inverse kinematics is present.

## Capturing commands and retaining a state

WALK_START and WALK_STOP are single events. Their high-gamma relays recruit
START_REQUEST or STOP_REQUEST, each reinforced through its own high-gamma helper.
The request persists until the corresponding WALK/REST goal takes over. The
opposite command clears a pending request. Existing WALK_ENABLED/WALK_NUCLEUS
and REST_ACTIVE/REST_NUCLEUS loops retain the goal, with opposing clearing paths.

START_REQUEST_HG also captures PHASE_A_REQUEST. Each phase request has a
REQUEST → REQUEST_HG → REQUEST loop. Its helper excites that phase's OUT and
clears the opposite state and its feedback path. Once the new state is active,
DRIVE_HG clears its own request and helper. The OUT → DRIVE_HG → OUT loop retains
the selected state. Each DRIVE_HG inhibits the opposite OUT, DRIVE_HG and motor
feedback relay. This makes handoff a neural event rather than a Python decision.

State/request clearing uses strength 4. Successful state recruitment clears its
own handoff request at strength 64 because an upstream release burst may still
be arriving. Strength is a multiplier of the SDK's calculated inhibitory
reference, not a percentage of neurons suppressed. These paths are static.

## What flips the switch

The four hip output neurons selected by the active pattern feed its
MOTOR_FEEDBACK_HG. Their combined activity passes through FEEDBACK_BETA T5 →
BETA T5 → RELEASE T3. RELEASE excites the opposite phase's REQUEST. It also
inhibits its own two feedback Betas, allowing that pathway to recover.

| State | Hip outputs supplying its feedback |
| --- | --- |
| A | FL_HIP_NEG, RR_HIP_NEG, FR_HIP_POS, RL_HIP_POS |
| B | FL_HIP_POS, RR_HIP_POS, FR_HIP_NEG, RL_HIP_NEG |

The neural outputs are the feedback source. No per-step phase, movement progress,
oscillator signal or motor state is sent back by Python. This path reflects
command activity, not joint completion or confirmed ground contact. It combines
the four outputs; it does not implement a strict four-way AND.

A handoff request persists through competition until the new state takes over.
There can be propagation gaps between states and between actuator outputs. The
adapter always applies the current motor frame, including quiet frames.

## Motor assignment

| State | FL/RR | FR/RL |
| --- | --- | --- |
| A | HIP_NEG, KNEE_NEG | HIP_POS, KNEE_POS |
| B | HIP_POS, KNEE_POS | HIP_NEG, KNEE_NEG |

Positive hip rotation advances the foot in the bundled Spot model. Knee POS
flexes and NEG extends in the configured range. Abduction is mirrored: swing
uses NEG on left legs and POS on right legs. Each state relay excites the
appropriate local Beta T5, which excites its named actuator output.

The opposite state inhibits that Beta and output at strength 4. Local opposing
Betas also inhibit one another and their opposite outputs at the reference
strength of 1. Knee extension uses a local high-gamma veto relay so its reflex
can release its own extension without changing the shared switch.

Knee flexion is +0.35 rad and extension −0.08 rad relative to neutral. This is
mechanical amplitude calibration. TNorm does not encode angle, force or speed.
The configured limits do not establish a validated foot trajectory.

## Reflex and gait meet at the extension output

Each leg has a separate REFLEX_EXTENSION_BETA, excited only by its local
REFLEX_HG. Both this Beta and the gait extension Beta excite the existing
KNEE_NEG output. The reflex therefore bypasses the switch while still passing
through a motor Beta. Each Beta has one immediate excitatory source; adding the
sensory reflex does not resize or dilute the gait Beta.

REFLEX_HG inhibits its local flexion Beta/output and local extension-veto relay.
The reflex extension Beta recruits RESET_HG, which inhibits its own reflex and
clears ACTIVE. No reflex connection targets another leg or any switch node.
See [REFLEX.md](REFLEX.md).

## Allocation and operating points

| Population | Rhythm / TNorm | Neurons each |
| --- | --- | --- |
| Switch request and state relays | High-gamma 10 | 1 |
| Motor feedback relay | High-gamma 10 | 4 |
| Feedback Beta | Beta 5 | 7 |
| Downstream Beta | Beta 5 | 11 |
| Release | Beta 3 | 15 |
| Local gait motor Beta | Beta 5 | 2 |
| Local extension-veto relay | High-gamma 3 | 1 |
| Local reflex | High-gamma 3 | 24 |
| Reflex extension Beta | Beta 5 | 24 |
| Reflex reset | High-gamma 3 | 24 |

The builder calculates these widths from the declared relationships. T10 is used
for the small retained command/state relay paths; the sensory reflex uses T3.
No claim is made that T3 is universally optimal or that larger populations alone
produce coordination.

The complete graph has 62 OPUs, 39 one-neuron outputs and eight external input
populations: 109 populations, 441 connections, 520 total neurons and 414,400 bytes
of connection matrices. Build on the device remains authoritative.

## Learning scope

Four connections use STDP3, GAIT_REWARD and reward_type LTP: each RELEASE inhibits
its own FEEDBACK_BETA and BETA, initially at strength 4. This targets recovery of
the handoff pathway. Eligibility stores recent source/receiver timing; dopamine
uses that eligibility to adjust the selected inhibitory connections. LTP follows
eligibility direction; it does not mean every update strengthens inhibition.

All state retention, state interlocks, request capture, motor vetoes, local
antagonists, reflex paths and excitation are static. `walk` sends no positive
reward. `learn` supplies reward from new upright forward progress. A static graph
can also be authored with `python design_brain.py --static`. First verify the
behavior, then evaluate adaptation using actual trajectories and weight telemetry.
