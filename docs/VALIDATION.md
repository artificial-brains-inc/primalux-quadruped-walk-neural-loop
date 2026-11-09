# Validation

SDK 0.4.2 validates the saved design, and the compatible local builder accepts
its construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json) records **549 total
neurons**, 77 external neurons, 173 populations, 759 connections and 295,820 bytes
of connection matrices. Other prepared-image data also consumes the 32 MiB
budget; device preparation remains authoritative.

**107 application tests pass.** They cover command capture without neural ACK,
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

## Neural coordination checks

[SAME_SIDE_CHECK.json](SAME_SIDE_CHECK.json) records six current-design cases and
one baseline comparison using native cell updates, static weights and explicit
local initialization, connectivity and fatigue assumptions. Inputs are synthetic
START, STOP, contact and tilt observations. The harness does not inject motor
outputs or gait phases. This is not a compiled device image, an FPGA-equivalence
check, a Webots physics run or a test of weight updates.

The all-contact comparison reduced the median rear-HIP_NEG to same-side
front-HIP_POS interval from 15 to 5 harness frames on both sides. Rear drive was
active at every checked front onset in the current all-contact case. This is
neural command coordination, not a measured backward force or physical benefit.
The added branches do not bypass the front's completion and stop clearers.

| Current-design case | Observed result |
| --- | --- |
| All feet report contact | Repeated sequences, with same-side motor output overlap |
| No foot reports contact | Initial front movement can start; no contact-ready latch or phase B |
| Rear-left contact withheld until frame 650 | Its confirmation and phase B remain blocked until contact arrives |
| Varied initial phases and coupling | Repeated coordinated sequences |
| Left tilt during walking | Left fast reflex outputs respond; right fast outputs remain inactive |
| STOP at frame 700, START at 900 | Movement clears and coordinated sequences resume |

The six cases have no simultaneous A/B readouts or opposing hip/knee outputs in
the checked walking interval. All normal motor outputs clear after the final
STOP. The report also records the branch activity and timing used in those checks.
These timings are not predictions of device or Webots timing.

[CONTACT_CHECK.json](CONTACT_CHECK.json) and [SWITCH_CHECK.json](SWITCH_CHECK.json)
retain their earlier design hashes. Their cases were not rerun under those old
report identities; use SAME_SIDE_CHECK for the current design. No local report
establishes dopamine-driven weight changes. Only the four inhibitory release
returns have STDP3/LTP; all excitatory, contact, reflex and same-side relay paths
are static.

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
