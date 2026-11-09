# Validation

SDK 0.4.2 validates the saved design, and the compatible local builder accepts
its construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json) records **551 total
neurons**, 77 external neurons, 171 populations, 751 connections and 297,444 bytes
of connection matrices. Other prepared-image data also consumes the 32 MiB
budget; device preparation remains authoritative.

**106 application tests pass.** They cover command capture without neural ACK,
SDK dispatch, actuator calibration, physical-input encoding, reward, recovery,
Stop/save, installer repair, bundled assets, saved-graph agreement and recording.
Contact checks cover all four device names, bumper type, invalid measurements,
suspension, shutdown clearing and the absence of a direct contact-to-motor path.

The real SDK encoder test preserves 48 tilt, 16 contact and 10 reward neurons in
one atomic input frame. The blocked-HTTP test delivers all 30 native motor frames
while input publication is stalled, then sends only the newest unsent capture,
including its matching contacts. Controller tests verify that raw foot readings,
transmitted contact vectors and observation records agree. Mocked Webots devices
cannot establish physical contact or gait stability.

The model tests verify that each SpotLeg instance gets a named bumper around the
original distal foot cylinder and that its duplicate parent collider is removed.
The pad dimensions and transform are unchanged. Each pad must have an explicit
positive-mass Physics body; the regression check rejects the previous kinematic
sensor. A separate check verifies that the visible floor and collision floor
share one Box with its top at z=0. Every bundled asset matches its manifest.

The correction follows Webots R2025a's TouchSensor implementation: a physical
sensor gets a body and a fixed joint to its parent. A sensor without Physics
does not inherit its parent's physical body. The official bumper sample also
uses an explicit Physics mass. Each new pad adds 10 g; no other body parameters
are changed. Webots is not installed by this package and was not run here.
This identifies and repairs the missing load-bearing body in the model; it
does not constitute a physical walking or collision-depth measurement.

## Neural contact checks

[CONTACT_CHECK.json](CONTACT_CHECK.json) matches the current design hash and
retains seven full-circuit local cases using native cell updates, static weights
and explicit harness assumptions. Those cases were recorded before the uniform
LTP selection. Construction comparison confirms identical populations and
initial connection parameters; only the four release reward directions change.
The report records the source hash and this equivalence check. It does not
validate LTP weight updates or the Webots physics correction. Inputs are synthetic START, STOP, contact and
tilt observations; the harness does not inject gait phases or motor outputs.

| Case | Observed result |
| --- | --- |
| All feet report contact | Repeated contact-qualified sequences in all four legs |
| No foot reports contact | Front return extends; rear handoff and phase B remain blocked |
| Front-right contact delayed until frame 900 | No earlier confirmation; rear-left movement begins at frame 910 |
| Varied initial phases and coupling | Repeated sequences and explicit STOP clearing |
| Contact delivered only every tenth neural frame | Repeated sequences in all four legs |
| Rear-left contact absent | Rear-left return occurs; its confirmation and phase B stay blocked |
| Left tilt during walking | Left fast reflex outputs respond; right fast outputs remain inactive |

Across these cases, the checked interval had no simultaneous A/B phase readouts
and no knee flexion/extension output conflicts. Motor and contact-ready activity
was cleared after STOP. The missing/delayed-contact cases retained front return
extension while the neural handoff was blocked. These are local harness results,
not timing guarantees for the device or a measured foot trajectory.

An isolated gate check also tested each cue alone, both together, delayed contact,
contact disappearing after confirmation, and clearing for reuse. Single-cue
conditions did not activate the ready latch. The qualified event remained latched
through later contact loss and was cleared by the next movement's clearing path.

The previous [SWITCH_CHECK.json](SWITCH_CHECK.json) retains its earlier design
hash. It is evidence about the preceding return/reflex circuit, not validation
of the contact graph. The current contact report does not test dopamine-driven
weight changes. Release returns retain STDP3/LTP, normal support inputs retain
STDP3/LTP, and every contact/reflex edge is static.

## Check on the actual system

Run `walk` first. Confirm that planted pads report 1 and lifted pads report 0.
Compare `contact-inputs.jsonl`, raw observations and individual neural telemetry:
contact HG, contact veto, match, ready and downstream handoff. Input queue
acceptance does not prove neural processing or physical support.

A ready latch means a collision was observed during return. It does not prove a
completed airborne swing, adequate supported load, a backward impulse, successful
weight transfer or balance. Ground forces and physical walking have not been
validated here. Evaluate those in Webots before interpreting a learning run.

After the physical behavior works, compare matched runs using progress, falls,
stalled intervals and available weight observations. Supervisor recovery remains
explicit simulator assistance and is not learned self-righting.
