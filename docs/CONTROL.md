# Controller responsibilities and timing

## What crosses the boundary

The adapter sends one atomic START-or-STOP snapshot together with ACK, at startup
or on an explicit W/S keypress. A fresh transport ACK establishes receipt. The
adapter then clears only the ACK input through the SDK's named-population update;
it leaves the requested command asserted without republishing it.

Each subsequent native output frame is applied to the body and inspected for
command confirmation. START requires WALK_ENABLED=1 and REST_ACTIVE=0; STOP
requires WALK_ENABLED=0 and REST_ACTIVE=1. Only then does the adapter clear the
command inputs. These checks confirm goal readouts; they do not select gait phases,
choose joint movements or claim the entire neural circuit has settled.

No phase, motor state or body-derived movement command is sent as an input. Once the goal
confirms, neural reinforcement and recurrence maintain activity. The regular loop
publishes no periodic command refresh. Holding a keyboard key does not resend it each frame;
a deliberate release and new press can issue another command. An explicit S can
replace a START still awaiting confirmation.

Only the transport ACK wait freezes physics. After ACK, the body advances exactly
once per native frame while the neural goal switches, including frames where REST
is still active. The adapter never fabricates a motor state or skips those frames
to wait for WALK. Diagnostic readouts cannot make the robot move; local motor
outputs alone drive the joints.

`ack_timeout_seconds` bounds the transport wait, then separately bounds goal
confirmation after ACK. Failure reports the requested command and latest WALK/REST
readouts and ends the session through SDK Stop/save. Missing native frames or an
output-stream timeout also stop the session. There is no automatic retry.

ACK confirms receipt, not completion of a neural decision. Clearing START on ACK
alone can withdraw its excitation and REST inhibition before the command circuit
has switched. The adapter separates transport receipt from goal confirmation.

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
reads phase, inhibitor, release, WALK, REST or startup-bias channels to
select a gait or posture. Those channels are diagnostics. Only local motor outputs move joints.

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
only when the binary value changes. The input holds that value between changes;
it is not a fabricated spike train. Startup, W/S commands and shutdown clear it.
Command clearing affects only START, STOP and ACK, never the reward input.
`rewards.jsonl` records accepted changes; every observation records its evidence.
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
