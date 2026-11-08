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

## Fast reflex and normal extension recruitment

REFLEX_HG drives a dedicated 24-neuron Beta T5 and inhibits local flexion and
its extension-veto relay. The Beta drives KNEE_REFLEX_EXTEND, calibrated to
−0.22 rad at up to 3.0 rad/s. Normal KNEE_NEG remains −0.08 rad at 1.5 rad/s.

The reflex motor output also excites NORMAL_RELAY_HG T10 (one neuron), which
excites the actual normal knee extension Beta through STDP3/LTP. Normal phase
and teaching sources are both high-gamma, with one neuron each. The resulting
normal extension Beta has four neurons. This small relay carries motor
activity; the sensory reflex and its motor Beta still have 24 neurons each.

The existing RESET_HG ends the upstream reflex drive. A separate
KNEE_REFLEX_EXTEND → OUTPUT_RESET_HG → inhibitory return clears the bistable
fast output from its own activity. No controller timer sets its burst duration.
Repeated sensory evidence can recruit new bursts. Normal extension persists or
clears through its existing gait/antagonist/REST paths. ACTIVE remains diagnostic.
No reflex connection targets another leg or a shared switch node.
See [REFLEX.md](REFLEX.md).

## Allocation and operating points

| Population | Rhythm / TNorm | Neurons each |
| --- | --- | --- |
| Switch request and state relays | High-gamma 10 | 1 |
| Motor feedback relay | High-gamma 10 | 4 |
| Feedback Beta | Beta 5 | 7 |
| Downstream Beta | Beta 5 | 11 |
| Release | Beta 3 | 15 |
| Normal knee extension Beta | Beta 5 | 4 |
| Other local gait motor Beta | Beta 5 | 2 |
| Local extension-veto relay | High-gamma 3 | 1 |
| Local reflex | High-gamma 3 | 24 |
| Reflex extension Beta | Beta 5 | 24 |
| Reflex reset | High-gamma 3 | 24 |
| Reward relay | High-gamma 10 | 10 |
| Reward population | Dopaminergic 3 | 17 |
| Normal-path relay / output reset | High-gamma 10 | 1 each |

The builder calculates these widths from the declared relationships. T10 is used
for the small retained command/state relay paths; the sensory reflex uses T3.
No claim is made that T3 is universally optimal or that larger populations alone
produce coordination.

The complete graph has 70 OPUs, 43 one-neuron outputs and eight external input
populations: 121 populations, 481 connections, 573 total neurons and 425,572 bytes
of connection matrices. Build on the device remains authoritative.

## Learning scope

GAIT_REWARD is a dopaminergic T3 population with 17 neurons. It receives a
10-neuron high-gamma relay driven by one 10-neuron outcome input population.
Its outcome class is positive upright forward progress; zero means no reward.

Four connections use STDP3, GAIT_REWARD and reward_type LTP: each RELEASE inhibits
its own FEEDBACK_BETA and BETA, initially at strength 4. This targets recovery of
the handoff pathway. Eligibility stores recent source/receiver timing; dopamine
uses that eligibility to adjust the selected inhibitory connections. LTP follows
eligibility direction; it does not mean every update strengthens inhibition.

Four more STDP3/LTP connections excite the normal extension Beta from that leg's
NORMAL_RELAY_HG. Their source is actual reflex motor output activity. This is
deliberate adaptation of excitatory recruitment; it can change that relationship's
computation. It does not create activity without a source or prove anticipation
before a tilt. The fixed fast branch works before learning.

All state retention, state interlocks, request capture, motor vetoes, antagonists,
fast reflex excitation and reset remain static. `walk` sends no positive
reward. `learn` supplies reward from new upright forward progress. A static graph
can also be authored with `python design_brain.py --static`. First verify the
behavior, then evaluate adaptation using actual trajectories and weight telemetry.
