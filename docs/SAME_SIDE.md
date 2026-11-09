# Rear stance and same-side front advance

The intended overlap is rear-left backward drive with front-left forward swing,
and rear-right backward drive with front-right forward swing. This is a motor
relationship inside the brain. Python does not select a leg or schedule a phase.

## Separate landing from the backward stroke

Each rear leg still starts landing through RETURN_BETA → KNEE_NEG. DONE retains
that extension, and measured foot contact qualifies the phase handoff.

Rear DONE no longer recruits HIP_NEG_BETA or clears the forward HIP_POS output.
It still clears the internal forward hip Beta. The output deliberately retains
the forward target through landing, with explicit clearing by the support phase,
the opposing motor Beta or REST. This prevents an early return to neutral and an
early backward target while the front is still waiting for its phase.

The new phase recruits both rear HIP_NEG_BETA and the same-side front MOVE_HG.
The rear support Beta is Beta T5, two neurons, receiving one operand unit from
its phase drive. Knee landing and reflex extension remain independent of this
hip coordination.

## Couple the motor activity

| Rear motor output | Fixed relay | Front motor output |
| --- | --- | --- |
| RL_HIP_NEG | LEG_FL_STANCE_HANDOFF_HG | FL_HIP_POS |
| RR_HIP_NEG | LEG_FR_STANCE_HANDOFF_HG | FR_HIP_POS |

Each relay is **high-gamma T10, one neuron**. It relays a one-neuron motor output;
it is not a reflex population or an amplitude multiplier. Every connection in
these two branches is static. The front's ordinary Beta → HIP_POS pathway also
continues, while the new branch recruits that same output from rear motor activity.
The SDK requires output feedback to pass through an OPU.

Front DONE and the front's support phase each inhibit its relay at strength 64.
STOP/REST inhibit the relay at strength 4. Existing front HIP_POS clearing by
DONE, its support phase, its antagonist and REST remains. These clearers prevent
a held rear stance command from repeatedly restarting a completed front swing.
Inhibitory strengths are SDK reference multipliers, not percentages or TNorms.

Only the four inhibitory macro release-feedback paths use STDP3/LTP. Both new
relays, all excitatory connections, the contact circuit and every reflex path
remain static. No new input, output channel or controller rule is required.

## What to observe

Compare rear HIP_NEG onset with same-side front HIP_POS onset in native output
records. Then inspect measured hip positions and foot contacts: output overlap
does not prove useful ground force or successful weight transfer. Contact is
binary collision evidence; it cannot establish that the foot is pushing backward.

The local static comparison reduced the median rear-to-front output interval
from 15 to 5 harness frames on both sides. Those are local neural harness frames,
not measured Webots seconds or a device timing guarantee. See
[SAME_SIDE_CHECK.json](SAME_SIDE_CHECK.json) and [VALIDATION.md](VALIDATION.md).

The complete graph has 549 neurons, including the unchanged 77 external neurons.
The two added relays use two neurons; the rear support Betas each shrink from
four to two when their extra DONE source is removed. All actuator speeds,
excursions, physics settings, contact bodies and recovery settings remain fixed.
