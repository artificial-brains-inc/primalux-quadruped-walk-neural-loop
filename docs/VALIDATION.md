# Validation

SDK 0.4.2 validates the saved design, and the compatible local builder accepts
its construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json) records **569 total
neurons**, 77 external neurons, 169 populations, 723 connections and 300,860 bytes
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

[CONTACT_SWITCH_CHECK.json](CONTACT_SWITCH_CHECK.json) records ten current-design
cases using native cell updates, fixed weights and explicit local initialization,
connectivity and fatigue assumptions. Inputs are synthetic START, STOP, contact
and tilt observations. No motor outputs or gait phases are injected. This is
not a compiled device image, an FPGA-equivalence check, a Webots physics run or
a test of plastic weight updates.

| Current-design case | Observed result |
| --- | --- |
| All feet report contact | Repeated A/B sequences; both RELEASE branches remain active |
| No foot reports contact | Initial front-right movement only; no rear handoff or phase B |
| Rear-left contact withheld until frame 650 | A remains selected; B and front-left movement follow contact |
| Front-right contact withheld until frame 650 | Rear-left movement waits for that front contact |
| Rear-left pulse at frame 120, before return | No rear-left READY or phase B; early contact is not reused |
| One rear-left pulse at frame 650, during return | One B entry; no further B without fresh eligible contact |
| Standing with contact, without START | No phases, READY events or leg movements |
| Varied initial phases and coupling | Repeated A/B sequences and active reset branches |
| Left tilt during walking | Left fast reflex outputs respond; right fast outputs remain inactive |
| STOP at frame 700, START at 900 | All motors clear while stopped; sequences resume after START |

All ten cases have no simultaneous A/B readouts or opposing hip/knee outputs
in the checked interval. Normal, push and fast-reflex motor outputs are quiet
after final STOP. The report records the stimulus schedule, activity and design
hash. Its frame intervals are not predictions of device or Webots timing.
RELEASE activity confirms that the reset branches are recruited; it does not
establish eligibility, dopamine firing or learned weight changes.

The older SAME_SIDE_CHECK, CONTACT_CHECK and SWITCH_CHECK reports retain their
original design hashes and do not validate this graph. Use CONTACT_SWITCH_CHECK
for the current design. Only four inhibitory release returns have STDP3/LTP;
all excitatory, contact and reflex paths are static.

## Check on the actual system

Run `walk` first. Confirm that planted pads report 1 and lifted pads report 0.
Compare `contact-inputs.jsonl`, raw observations and individual neural telemetry:
contact HG, return veto, match, ready, FEEDBACK_BETA and opposite phase request. Input queue
acceptance does not prove neural processing or physical support.

A ready latch means a collision was observed during return. It does not prove a
completed airborne swing, adequate supported load, a backward impulse, successful
weight transfer or balance. Ground forces and physical walking have not been
validated here. Evaluate those in Webots before interpreting a learning run.

After the physical behavior works, compare matched runs using progress, falls,
stalled intervals and available weight observations. Supervisor recovery remains
explicit simulator assistance and is not learned self-righting.
