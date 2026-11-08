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
appropriate front-leg Beta T5, which excites its named actuator output.
The rear legs instead receive their corresponding front hip output through a
one-neuron high-gamma T10 relay: RR follows FL and RL follows FR. Each rear leg
has a relay for each switch state. The opposite state, STOP and REST clear
these relays. Reflexes do not pass through them. This orders command activity;
it does not measure when the front foot has completed a stroke.

The opposite state inhibits that Beta and output at strength 4. Local opposing
Betas also inhibit one another and their opposite outputs at the reference
strength of 1. Knee extension uses a local high-gamma veto relay so its reflex
can release its own extension without changing the shared switch.

Knee flexion is +0.35 rad and extension −0.08 rad relative to neutral. This is
mechanical amplitude calibration. TNorm does not encode angle, force or speed.
The configured limits do not establish a validated foot trajectory.

## Direct reflex and normal extension recruitment

REFLEX_HG contains 24 high-gamma T5 neurons. It directly excites
KNEE_REFLEX_EXTEND, calibrated to −0.22 rad at up to 3.0 rad/s. The reflex does
not wait for a Beta. Normal KNEE_NEG remains −0.08 rad at 1.5 rad/s.

The same REFLEX_HG directly excites the actual regular knee extension Beta
through STDP3/LTP. The normal gait drive and reflex HG both have role `operand`
and `units=1` into this Beta T5. This is the guide's OR starting construction:
either gait or reflex evidence can recruit normal extension. Equal canonical
units express equal contributions despite the different source widths; units
are not neuron counts or arbitrary gains. The builder allocates 24 neurons to
each regular extension Beta. Learning can change reflex recruitment from this
initial relationship. No output-derived teaching relay is present.

KNEE_REFLEX_EXTEND recruits OUTPUT_RESET_HG T10 (one neuron), which clears that
output and ACTIVE and inhibits the reflex trigger at strength 4. Reset therefore
begins after the fast output fires. Continued evidence may recruit another burst.
The trigger also inhibits local flexion Beta/output and the normal extension-veto
relay at strength 64. ACTIVE has no outgoing edges. There is no dedicated reflex
Beta, separate upstream reset population, corner veto or controller timer.
See [REFLEX.md](REFLEX.md).

## Allocation and operating points

| Population | Rhythm / TNorm | Neurons each |
| --- | --- | --- |
| Switch request and state relays | High-gamma 10 | 1 |
| Motor feedback relay | High-gamma 10 | 4 |
| Feedback Beta | Beta 5 | 7 |
| Downstream Beta | Beta 5 | 11 |
| Release | Beta 3 | 15 |
| Normal knee extension Beta | Beta 5 | 24 |
| Other local gait motor Beta | Beta 5 | 2 |
| Local extension-veto relay | High-gamma 3 | 1 |
| Local reflex | High-gamma 5 | 24 |
| Rear gait relays (four) | High-gamma 10 | 1 |
| Reward relay | High-gamma 10 | 10 |
| Reward population | Dopaminergic 3 | 17 |
| Reflex output reset | High-gamma 10 | 1 |

The builder calculates these widths from the declared relationships. T10 is used
for the small retained command/state relay paths; the sensory reflex uses T5.
No claim is made that T5 is universally optimal or that larger populations alone
produce coordination.

The complete graph has 62 OPUs, 43 one-neuron outputs and eight external input
populations: 113 populations, 457 connections, 461 total neurons and 305,284 bytes
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
REFLEX_HG. Their source is the reflex population itself, so pre/post firing at
that direct connection contributes eligibility. This is
deliberate adaptation of excitatory recruitment; it can change that relationship's
computation. It does not create activity without a source or prove anticipation
before a tilt. The fixed fast branch works before learning.

All state retention, state interlocks, request capture, motor vetoes, antagonists,
fast reflex excitation and reset remain static. `walk` sends no positive
reward. `learn` supplies reward from new upright forward progress. A static graph
can also be authored with `python design_brain.py --static`. First verify the
behavior, then evaluate adaptation using actual trajectories and weight telemetry.
