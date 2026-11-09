# One switch, ordered push/swing sequences

A and B are the two retained states of one neural switch. A orders FR then RL;
B orders FL then RR. Each movement has an early push before knee flexion and a return-to-support stage. Each joint has opposing local
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

A orders FR then RL; B orders FL then RR. Each leg has MOVE, PUSH, SWING_READY
and DONE activity. Front DONE recruits a Beta T3 handoff into the rear leg's
MOVE_HG. Rear DONE_HG supplies the macro state's MOTOR_FEEDBACK_HG →
FEEDBACK_BETA T5 → BETA T5 → RELEASE T3. RELEASE captures the opposite request.
The same four inhibitory RELEASE returns retain their STDP3/LTP metadata.

This sequence uses internal neural activity. The return begins from an actual
knee flexion output rather than from the earlier hip command, so the leg's
knee command has started before it recruits the return. It is still command
history, not joint completion or confirmed ground contact.

## Early push and local return

MOVE_HG excites the normal swing Betas and PUSH_HG in parallel. PUSH_HG directly
excites KNEE_PUSH and inhibits KNEE_POS output at strength 64. The push output
feeds back into its HG to retain activity through upstream gaps. Hip Beta
recruits a retained SWING_READY output/HG loop; readiness clears PUSH_HG and
KNEE_PUSH at strength 64. The normal pathway continues after this local clearing.
Hip and abduction activity may begin while preparation finishes; knee flexion
follows the push. The controller imposes no delay or minimum stroke duration.

KNEE_POS recruits RETURN_BETA T3, then DONE/DONE_HG. RETURN_BETA directly excites
KNEE_NEG and inhibits KNEE_POS and the extension-output veto at strength 64.
DONE_HG retains those direct paths, so landing does not wait for a further
support-Beta stage. It also inhibits local movement and readiness, and excites
the normal support Betas. Each support Beta accepts
one unit from the opposite macro state and one from local DONE. The opposite
macro state clears the local sequence for reuse. Rear movement receives the
front's HANDOFF_BETA, not a front motor or reflex output. See [PUSH.md](PUSH.md).

## Reflex and ordinary extension

Each 24-neuron REFLEX_HG T5 has a fixed direct connection to the fast extension
output and a fixed operand connection into the existing regular
extension Beta T5. Regular extension accepts one canonical unit each from
macro support, local DONE and reflex HG, using the Beta T5 OR construction as
its starting relationship. STDP3/LTP is on macro support → regular extension
Beta, one connection per leg. Local DONE → Beta and Beta → output stay static.
The fixed reflex can recruit postsynaptic Beta activity that contributes to
eligibility when the normal presynaptic support source also fires with suitable
timing. Learning adapts normal support recruitment.

The local SWING_READY_HG recruits EXTENSION_VETO_HG T10, which inhibits ordinary
extension output at strength 64. It does not inhibit the extension Beta. Knee
competition is enforced through the state/output vetoes rather than continuous
opposing Beta inhibition. This preserves the Beta's ability to respond to reflex
evidence during swing. Hip and abduction keep their local Beta antagonism.

Reflex HG inhibits its own flexion Beta/output and its extension-veto relay at
strength 64. It does not change a shared phase or another leg. The fast output
recruits RECOVERY_BETA T3 → OUTPUT_RESET_BETA T3. The latter clears fast output
and ACTIVE and inhibits its own trigger at strength 4. This replaces immediate
one-HG clearing. ACTIVE remains diagnostic. See [REFLEX.md](REFLEX.md).

## Allocation and operating points

| Population | Rhythm / TNorm | Neurons each |
| --- | --- | --- |
| Command, state and readiness HG helpers | High-gamma 10 | 1 |
| Macro motor feedback HG | High-gamma 10 | 1 |
| Macro feedback / downstream / release | Beta 5 / Beta 5 / Beta 3 | 2 / 4 / 7 |
| Front MOVE / PUSH | High-gamma 10 | 1 |
| Rear MOVE / PUSH | High-gamma 10 | 2 |
| Local RETURN / front HANDOFF | Beta 3 | 2 |
| Regular knee extension Beta | Beta 5 | 24 |
| Front swing / rear swing Betas | Beta 5 | 2 / 4 |
| Other support Betas | Beta 5 | 4 |
| Local extension-output veto | High-gamma 10 | 1 |
| Local reflex HG | High-gamma 5 | 24 |
| Reflex recovery / output reset | Beta 3 / Beta 3 | 2 / 4 |
| Reward relay / reward | High-gamma 10 / Dopaminergic 3 | 10 / 17 |

The compatible builder calculates these widths from the declared relationships.
The graph has 84 OPUs, 55 one-neuron outputs and eight external populations:
147 populations, 663 connections, 503 total neurons and 292,796 bytes of
connection matrices. Device preparation remains authoritative.

## Learning scope

Four RELEASE inhibitory returns and four REFLEX_HG → regular extension Beta
excitatory connections use STDP3, GAIT_REWARD and reward_type LTP. Eligibility
reflects recent source/receiver timing; dopaminergic activity acts on that
eligibility. LTP follows its sign and does not mean every update strengthens.
The fast motor branches, state retention, sequencing, vetoes and resets remain
static. `walk` sends no positive reward; `learn` rewards new upright forward
progress. Stationary recovery alone is not that outcome.

Check the static behavior first. Use internal spike recording and weight
observation to assess recruitment and learning, and actual robot measurements
to assess physical benefit. A wire or accepted reward publication proves neither.
