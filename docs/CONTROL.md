# Controller responsibilities and timing

The session has no maximum duration. Elapsed wall time is recorded for analysis
and does not end a run. Q, closing Webots or stopping the SDK application ends
the session through Stop/save.

## What crosses the boundary

The adapter queues one atomic START-or-STOP event at startup or on a W/S
keypress. Explicit simulator recovery also requests one STOP and, if requested,
one START after settling. The device consumes each input event in a neural step;
it does not maintain START as a level until a later zero event.

There is no neural ACK handshake. The legacy isolated ACK input is cleared once
at startup and never stimulated. Its output is never used for synchronization.
The eight foot-state populations and four local stage/event circuits define the contract.
Build the supplied design before running this package.

Neural request latches capture the command and maintain its drive internally.
The corresponding goal nucleus clears the request after taking over. An opposite
command cue can cancel it. Python observes START's WALK=1/REST=0 or STOP's
WALK=0/REST=1 readouts. It supplies no command repeats or phase choices, and
confirmation does not send another input snapshot. An explicit S can supersede
a pending START; a fresh W keypress can issue a new event.

One worker handles input HTTP requests. Commands have priority over unsent
feedback, and command submission discards any pre-command unsent feedback.
The motor loop keeps applying every native frame while a request is in flight
or goal confirmation is pending. Only frames newer than the output cursor at
HTTP acceptance can confirm a command. `command_timeout_seconds` bounds goal
confirmation after HTTP acceptance; it is not a gait duration or ACK timeout.
Failure reports WALK, REST and both request readouts and triggers SDK Stop/save.

Tilt, four foot contacts and reward are captured after each body step and submitted together through
`publish_sensor_frame`, using the SDK's `reward_population` encoder for reward.
If publication is slower than sensing, each new capture replaces the previous
unsent capture. No motor frames are dropped. An in-flight HTTP request cannot be
cancelled; the worker does not claim zero transport latency. The worker is joined
before final input clears, log closure and Stop/save, so it cannot publish after
shutdown. Input failures propagate to the normal error cleanup.

One native output frame advances 32 ms of simulation time (two 16 ms physics
substeps). Webots runs in fast mode with rendering, so this duration does not add
a realtime sleep. The motor readout remains authoritative on every native frame;
there is no host minimum stroke duration or wait-until-target rule. Queue depth
is printed and logged. [Timing and measured cutoffs](../TIMING.md).

## Actuator decoding

For every joint independently, the adapter calculates the difference between its
positive and negative one-neuron outputs. A positive difference selects the
configured positive excursion from neutral; a negative difference selects the
negative excursion. Both zero or both active select neutral. The resulting angle
is sent to the Webots position servo, with the configured speed limit.

Neutral positions follow the official Spot sample's standing posture: left
abduction -0.1 rad, right abduction +0.1 rad, hip and elbow 0 rad. Excursions are
explicit first-design actuator calibration, within the model's joint limits.
They are not learned values or a verified foot trajectory. The adapter never
reads phase, handoff-request or release channels to select a gait.
During ordinary walking only local motor outputs move joints. Explicit simulator
recovery holds neutral targets, waits for exclusive REST and quiet motor outputs,
then restores the initial robot state. See [Recovery](RECOVERY.md); this assistance
does not select a gait phase or demonstrate learned self-righting.

The four additional piston motors in Spot's leg geometry are not primary gait
actuators; the official sample likewise commands the 12 abduction, rotation and
elbow motors. This example uses that same primary actuator interface.

## Physical outcome reward

Joint positions, GPS, inertial orientation and gyro are logged after each applied
motor frame and its completed Webots step. In `learn` mode, GPS and orientation
also supply one binary outcome carried by a 10-neuron reward input population. No per-joint error or desired trajectory
is computed.

After a confirmed START, capture the initial position and heading. For each body
step, project displacement along that fixed forward heading. Reward is 1 only if:

- Forward speed is at least 0.02 m/s over the step.
- Progress exceeds the episode's prior furthest forward position by more than
  0.00001 m, so reversing and retracing distance does not repeatedly earn reward.
- Absolute roll and pitch are each at most 0.35 rad, and body height is at least
  0.45 m above the bundled world's floor.

These are explicit initial outcome criteria in `config.json`, not learned values
or calibrated proof of good gait. New W confirmations start new measurement
episodes. Stationary, backward, sideways, low or excessively tilted motion earns
zero. Invalid measurements and simulation-time resets disarm reward until a new
START. Loss of exclusive WALK readout also disarms it; W can start a new episode.

### Reward classification and population size

| Population | Classification | TNorm | Neurons |
| --- | --- | --- | --- |
| GAIT_REWARD_IN | External outcome input | — | 10 |
| GAIT_REWARD_RELAY | High-gamma relay | 10 | 10 |
| GAIT_REWARD | Dopaminergic neuromodulator | 3 | 17 |

The compatible builder calculates 17 dopaminergic neurons from this pathway.
There is still one named reward input. Magnitude 1 is encoded as ten active input
neurons; magnitude 0 encodes ten zeros. Do not pass magnitude 10.

Each accepted event is classified as `positive_outcome` or `no_reward` in SDK
metadata and `rewards.jsonl`. Its `reason` records the physical condition.
No reward is not punishment. Only four inhibitory handoff-feedback connections
use STDP3 with `reward_type="LTP"` in the learning design: each leg's
STEP_BRAKE_BETA → STEP_HANDOFF_BETA. All other connections are static, including all excitatory
paths. There are no LTD connections.
LTP follows signed eligibility, so it does not guarantee every update strengthens
a connection.
The run's reward_classification records only handoff_feedback under reward_types.
Reward is a neuromodulator, not ordinary motor excitation.
Ten active input neurons do not prove that all 17 dopamine neurons fired. Check
individual neuron telemetry for that. A larger population also does not prove
that learning improves balance. The fixed reflex remains active without reward.

The adapter encodes the newest available reward evidence with its matching tilt and foot-contact
capture in one atomic SDK frame. Each transmitted 1 represents a newly measured
outcome; a prior 1 is not held by the device. Repeated all-zero feedback captures
are omitted. Startup and shutdown clear reward explicitly; pending commands and
recovery disarm new reward evidence. A command discards unsent pre-command
feedback but cannot retract a request already in flight.

`rewards.jsonl` records accepted transmitted events; every observation records
its measured evidence, including captures replaced before publication. There is
no deferred reward backlog or replay. This changes sensory sampling under a slow
transport, not graph weights, TNorms or neuron dynamics. A reward clear is
attempted on exit even if Webots closes; SDK Stop/save still runs if it fails.

Reward measurements follow body steps; reward delivery and neural eligibility
have transport delay. The recorded `native_step` identifies the frame that was
applied to produce the measured outcome, not the later step when hardware consumes
the reward. This is not an atomic reward-and-output protocol. Queue acceptance is
checked, but does not claim completed learning. Reward delivery does not introduce
a second ACK oscillator or select gait phases.

| Run mode | Actuator targets | External reward |
| --- | --- | --- |
| `learn` (default) | Local neural motor outputs | Physical outcome |
| `walk` | Local neural motor outputs | Held at zero |
| `rhythm` | Neutral standing posture | Held at zero |

`learn` requires exactly the four agreed inhibitory STDP3/LTP paths; `walk`
requires the static graph. The launcher rejects a mismatch before opening
Webots. Mode selection never rewrites or rebuilds a design.

## Physical tilt feedback

After each completed body step, the IMU roll/pitch sample is encoded as four
signed populations beyond a 0.08 rad deadband. Each population carries twelve
identical binary values, matching its 12-neuron design width. The SDK sends them
with the same capture's reward in one `publish_sensor_frame` call. Each transmitted
nonzero capture is fresh evidence; the worker never repeats a held capture.
New readings can replace older unsent readings while HTTP is busy. Repeated
all-zero feedback captures are omitted. This is sensory quantization, not a controller-side choice of leg or
support action. Gyro readings remain logged but are not new inputs.

Each local reflex receives compatible signs, inhibits its own knee flexion,
directly excites its fast extension output from high-gamma T5.
KNEE_REFLEX_EXTEND recruits RECOVERY_BETA T3 then OUTPUT_RESET_BETA T3; the
second stage clears the output and inhibits its trigger. The same high-gamma directly excites the regular extension
Beta through a fixed connection. Local stance drive → extension Beta
is also fixed. Only the four inhibitory handoff-feedback connections use
STDP3/LTP; every reflex connection is static.
No reflex inhibits another leg;
shared sensory evidence can recruit several independent reflexes.

KNEE_PUSH is a separate early extension output, calibrated to −0.12 rad at up to
3.0 rad/s. Its readiness and clearing are neural. The controller never reads
LEG_*_SWING_READY, LEG_*_DONE or LEG_*_CONTACT_READY to choose a motor target.

The four turn stages select FR → RL → FL → RR. Contact authorizes each
transition inside the graph. No motor-output shortcut or controller phase
selector recruits the next leg.

Final extension is the existing KNEE_NEG output. RETURN_BETA and DONE_HG drive
it directly and clear local knee flexion/output veto neurally, alongside the
regular support-Beta pathway. The decoder applies its existing −0.08 rad,
1.5 rad/s calibration; it does not infer a landing from a phase or DONE flag.

The decoder maps the fast motor output to the configured corrective excursion
and speed. Normal, push and fast extension use the largest commanded excursion, not summed
angles. If flexion and
extension are both commanded, they cancel as before; the graph is responsible
for suppressing flexion. When fast output clears, normal speed is restored on
the next frame. `joint_speed_limit_rad_s` records the applied limit, capped by
the model's maximum; it is not measured joint velocity. `REFLEX_*_ACTIVE` never
drives a motor. REST and pending
STOP inhibit the reflex neurally. Only explicit simulator recovery, `rhythm`
mode or `reflex.enabled=false` suspend tilt publication.

`tilt-inputs.jsonl` includes the source body frame, capture age at send and SDK
publication duration. Observations include pending feedback, replaced unsent
captures and completed publication counts in `input_transport`.
Hardware queue acceptance is checked; it is not proof of consumption in that
same neural step. No added ACK wait or host burst timer is used. Compare queue
backlog, received outputs and post-step body measurements when assessing latency.
A publication failure triggers the existing Stop/save cleanup.

## Foot contact feedback

Four enabled bumper TouchSensors report zero or one after each completed body
step. The controller encodes each reading as four CONTACT neurons and its binary
complement as four AIR neurons, in the same atomic frame as tilt and reward. It does not combine
contact with phase, select a leg, debounce by time, or wait for touchdown. Missing,
wrong-type or invalid sensor measurements fail visibly instead of becoming fake
contact. Recovery and shutdown clear both rails, rather than encoding no-contact.

`contact-inputs.jsonl` records accepted input events and their capture times;
`observations.jsonl` preserves every raw measurement even if an unsent capture
is replaced. The brain receives events, not a held contact level. A current
nonzero measurement is republished with each fresh transmitted capture.
[CONTACT.md](CONTACT.md) explains the local neural gate and its clearing paths.

## Internal neuron recording

`neuron-telemetry.jsonl` is read from the same authenticated completed-frame
stream used by the SDK's neuron viewer. Its `hello` record includes all neuron
identities. Each available `frame` preserves raw neuron/input bitsets and includes
`native_step` and `spike_counts` per population. Counts include zero-activity
populations. They are spike counts in that frame, not firing rates or proof of
physical support. A missing telemetry sample is `null`, not a zero-spike sample.

The observer runs independently of the motor loop. It never publishes inputs or
waits for a target. A recording gap, changed run or connection error is logged
and printed; it does not silently invent missing firing data. It does not restart
the brain. Send this file alongside observations and settings for diagnosis.

## Support motor offsets

Sixteen explicit HIP/ABD SUPPORT_POS/NEG outputs add fixed signed joint offsets.
The decoder reads those motor outputs only; PREPARE, ACTIVE and contact readouts
do not select a posture in Python. Neural ACTIVE vetoes exclude the swinging
leg. Opposing offsets cancel, and config validation checks the combined stroke
and support endpoints. See [SUPPORT.md](SUPPORT.md).
