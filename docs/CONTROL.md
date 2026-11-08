# Controller responsibilities and timing

## What crosses the boundary

The adapter publishes one atomic START-or-STOP event together with ACK at startup
or on a W/S keypress. Explicit simulator recovery also requests one STOP and,
if requested, one START after settling. The device consumes the input event in a neural step; it does
not maintain START as a level until a later zero event. A fresh transport ACK
confirms entry into its separate pathway, not the WALK/REST transition.

Neural request latches capture the command and maintain its drive internally.
The corresponding goal nucleus clears the request after taking over. An opposite
command cue can cancel it. Python waits for START's WALK=1/REST=0 or STOP's
WALK=0/REST=1 readouts; it supplies no command repeats or phase choices.

The zero ACK event after receipt and all-zero command snapshot after confirmation
are explicit idle observations. They must not be interpreted as releasing a held
stimulus. Reward and tilt channels are separate and are not included in command snapshots.

Only transport ACK waiting freezes physics. After ACK, each native output frame
produces one body step, including frames while the command remains pending.
`ack_timeout_seconds` separately bounds ACK waiting and goal confirmation.
Failure reports WALK, REST and both request readouts and triggers SDK Stop/save.
An explicit S can replace pending START; a new W keypress can issue a fresh event.

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
No reward is not punishment. The eight selected learning connections use STDP3
and reward_type LTP; the latter follows signed eligibility and does not guarantee
strengthening. Reward is a neuromodulator, not ordinary motor excitation.
Ten active input neurons do not prove that all 17 dopamine neurons fired. Check
individual neuron telemetry for that. A larger population also does not prove
that learning improves balance. The fixed reflex remains active without reward.

The adapter calls the SDK's `session.publish_reward("GAIT_REWARD_IN", value)`
for every qualifying body step. Each event represents a newly measured outcome;
a prior 1 is not held by the device. Repeated zeros are omitted. Startup, W/S
commands and shutdown send an explicit zero event.
Command clearing affects only START, STOP and ACK, never the reward input.
`rewards.jsonl` records accepted events; every observation records its evidence.
A reward clear is attempted on exit even if Webots closes; SDK Stop/save still runs
if that clear fails.

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

`walk` is not a guaranteed frozen-weight baseline: a plastic graph can retain
internal reward/eligibility state. Use the explicitly static graph for the
controlled comparison in TESTING.md. No mode simulates synthetic neurons in Python. `rhythm` also suspends tilt evidence.
During recovery every mode holds neutral targets and sends no positive reward.

## Physical tilt feedback

After each completed body step, the IMU roll/pitch sample is encoded as four
signed populations beyond a 0.08 rad deadband. Each population carries twelve
identical binary values, matching its 12-neuron design width. The SDK sends them
together in one
`publish_sensor_frame` call. Each nonzero sample is fresh evidence; repeated
unchanged tilt is not mistaken for a held input. Repeated all-zero frames are
omitted. This is sensory quantization, not a controller-side choice of leg or
support action. Gyro readings remain logged but are not new inputs.

Each local reflex receives compatible signs, inhibits its own knee flexion,
directly excites its fast extension output from high-gamma T5.
KNEE_REFLEX_EXTEND recruits RECOVERY_BETA T3 then OUTPUT_RESET_BETA T3; the
second stage clears the output and inhibits its trigger. The same high-gamma directly excites the regular extension
Beta through STDP3/LTP. No reflex inhibits another leg;
shared sensory evidence can recruit several independent reflexes.

KNEE_PUSH is a separate early extension output, calibrated to −0.12 rad at up to
3.0 rad/s. Its readiness and clearing are neural. The controller never reads
LEG_*_SWING_READY or LEG_*_DONE to choose a motor target.

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

`tilt-inputs.jsonl` includes the source body frame and SDK publication duration.
Hardware queue acceptance is checked; it is not proof of consumption in that
same neural step. No added ACK wait or host burst timer is used. Compare queue
backlog, received outputs and post-step body measurements when assessing latency.
A publication failure triggers the existing Stop/save cleanup.

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
