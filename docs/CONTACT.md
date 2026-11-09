# Foot contact in the neural loop

Each foot has one Webots bumper TouchSensor. Its existing distal collision pad
is the sensing surface; the duplicate parent collider is removed. The pad's
shape and location and the original forearm mass/inertia are preserved. Each
bumper now has a `Physics { density -1 mass 0.01 }` body. Webots attaches it to
the dynamic forearm with a fixed joint, so pad collisions transmit supporting
forces to the leg. This adds 10 g per pad, 40 g total. A kinematic child bumper
can detect overlap without supporting the leg; it is unsuitable for this
load-bearing foot pad. A bumper reports 1 for collision and 0 otherwise;
it does not report supported weight or ground force.

| Leg | Webots device | Input population | Input neurons |
| --- | --- | --- | --- |
| Front left | `front left foot touch` | `FOOT_FL_CONTACT` | 4 |
| Front right | `front right foot touch` | `FOOT_FR_CONTACT` | 4 |
| Rear left | `rear left foot touch` | `FOOT_RL_CONTACT` | 4 |
| Rear right | `rear right foot touch` | `FOOT_RR_CONTACT` | 4 |

The four identical bits in each input encode that foot's single measured state.
They are four neurons, not four independent sensors or force levels. This adds
16 sensory neurons, bringing the complete graph to 77 external neurons across
12 named inputs and 569 neurons in total. The compatible builder's allocation
is in [RESOURCE_CHECK.json](RESOURCE_CHECK.json).

## Return first, then contact-qualified handoff

The existing return pathway commands extension without waiting for contact.
That movement must remain available to bring a raised foot toward the floor.
The new gate qualifies only the handoff to the next leg or macro phase.

```mermaid
flowchart TD
  C["Measured foot contact"] --> H["Sensory HG"]
  C --> V["Return veto HG"]
  H --> M["Contact match HG"]
  V -->|Inhibits| M
  D["Local DONE HG"] -->|Inhibits| V
  M --> R["Contact-ready output"]
  R --> G["Contact-ready HG"]
  G --> R
```

The sensor drives the positive pathway. A parallel veto blocks contact from
being captured before the leg's return. DONE_HG inhibits that veto; it does not
excite MATCH or manufacture contact. The positive path has one more relay than
the veto path so unarmed contact does not arrive before its inhibition.

| Population / connection | Operating point | Role |
| --- | --- | --- |
| `FOOT_*_CONTACT_HG` | High-gamma T10, 4 neurons | Carries measured contact into MATCH |
| `LEG_*_RETURN_VETO_HG` | High-gamma T10, 4 neurons | Raw-contact-driven veto before return |
| DONE HG → return veto | Inhibitory strength 64 | Permits contact during return |
| `LEG_*_CONTACT_MATCH_HG` | High-gamma T10, 4 neurons | Accepts sensory activity when permitted |
| Return veto → match | Inhibitory strength 64 | Blocks unarmed contact |
| `LEG_*_CONTACT_READY` | Bistable output, 1 neuron | Captures the qualified event |
| `LEG_*_CONTACT_READY_HG` | High-gamma T10, 1 neuron | Retains the event and drives handoff |

The four-neuron sensory populations carry one foot's four-neuron input. These
high-gamma populations relay contact; they do not bypass the motor circuit.
The separate tilt reflex still uses 24 high-gamma T5 neurons and its fast output.
Inhibitory strengths multiply the SDK's calculated reference; they are not TNorms.

| Contact during local return | Neural consequence |
| --- | --- |
| Front right, in A | HANDOFF_BETA starts rear-left movement within A |
| Rear left, in A | FEEDBACK_BETA requests B, starting front-left movement and rear-left support |
| Front left, in B | HANDOFF_BETA starts rear-right movement within B |
| Rear right, in B | FEEDBACK_BETA requests A, starting front-right movement and rear-right support |

W seeds the initial A state. Thereafter contact advances this sequence. A rear
CONTACT_READY_HG reaches FEEDBACK_BETA directly, and that first Beta requests
the opposite phase. The later BETA → RELEASE branch handles reset without
delaying the request until RELEASE. The motor-output-to-motor-output shortcut
is removed. See [SAME_SIDE.md](SAME_SIDE.md).

## Retention and clearing

Once captured, CONTACT_READY and its HG retain the handoff event through brief
later contact gaps. This is event memory, not a continuous support guarantee.
Local MOVE_HG, the opposite/support phase and STOP/REST inhibit MATCH, READY
and READY_HG at strength 64. This clears a previous cycle's confirmation before
reuse. The sensory RETURN_VETO remains active when contact arrives during REST,
so standing contact cannot leak through while WALK initializes. No global brain
reset occurs.

The sensory relay is not a latch. Every transmitted nonzero sample is a new
input event. Input transport can delay contact qualification; the controller
never holds motor frames or adds an ACK while waiting for that evidence.

All contact connections are static. Only the four inhibitory release-feedback
connections use STDP3/LTP. Every excitatory connection is static, including
support drive → regular Beta. Every reflex connection also remains static.

## Inspect a run

The periodic console line prints raw `contacts` and active `contact_ready`
readouts. `observations.jsonl` contains every measured `foot_contact` and its
encoded `contact_inputs`. `contact-inputs.jsonl` contains accepted transmitted
captures, including capture age and native output step. Unsent captures can be
replaced by newer readings; the two logs make that visible.

In telemetry, follow contact HG → match → ready → FEEDBACK_BETA → opposite
phase request for a rear leg. Inspect DONE and RETURN_VETO alongside that path. While standing,
planted pads should read 1. A raised pad should read 0. If a foot has DONE=1 but
READY=0, inspect its physical contact and the gate; do not add a host timer to
force the next phase. Sensors remain available in `rhythm` mode while actuators
hold neutral and tilt evidence is suspended. Explicit simulator recovery
suspends contact input until recovery completes.

Contact during return qualifies the handoff even if that foot never left the
floor. This design does not require an airborne transition, measure backward
propulsion, estimate the centre of mass, or confirm that another leg has been
unloaded. Those are distinct observations and goals.

The Webots bumper API and collision requirements are documented in the
[official TouchSensor reference](https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/touchsensor.md).
The physical attachment follows Webots' [TouchSensor implementation](https://github.com/cyberbotics/webots/blob/R2025a/src/webots/nodes/WbTouchSensor.cpp)
and [physical bumper example](https://github.com/cyberbotics/webots/blob/R2025a/projects/samples/devices/worlds/bumper.wbt).
The sensor must own the collider that actually meets the floor. Tests verify
the packaged geometry and SDK path; physical collision readings still need the
Webots/device run described in [TESTING.md](TESTING.md).
