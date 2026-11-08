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
stimulus. The reward channel is separate and is not included in command snapshots.

Only transport ACK waiting freezes physics. After ACK, each native output frame
produces one body step, including frames while the command remains pending.
`ack_timeout_seconds` separately bounds ACK waiting and goal confirmation.
Failure reports WALK, REST and both request readouts and triggers SDK Stop/save.
An explicit S can replace pending START; a new W keypress can issue a fresh event.

One native output frame now advances 64 ms of simulation time (four 16 ms physics
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
reads phase, inhibitor, release or startup-bias channels to select a gait.
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
also supply the single binary reward. No per-joint error or desired trajectory
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
controlled comparison in TESTING.md. No mode simulates synthetic neurons in Python.
During recovery every mode holds neutral targets and sends no positive reward.
