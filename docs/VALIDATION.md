# Validation and limits

The SDK 0.4.2 validator and compatible 0.4.11 construction builder accept both
supplied designs. They use **751 total neurons**, including **93 external
neurons**, across **265 populations** and **1,277 connections**. Dense connection
matrices use **342,020 bytes**; other prepared-image data also consumes memory.
[RESOURCE_CHECK.json](RESOURCE_CHECK.json) records the learning root's hash and
every population. The static companion has identical topology, allocation and
initial strengths; it omits the eight learning annotations and has a different name.

All previously existing population widths are preserved. The four LOOP_HG
populations add six neurons total, and the two retry Betas per leg add 24.
No external neurons are added. Motor targets/speeds, support offsets, reflex
paths, world, foot-pad geometry and licenses are preserved.

## Application checks

All **122 application tests passed**. The suite verifies graph construction contracts, exact inhibitory
plasticity placement, static/learning parity, SDK command dispatch and input
encoding, controller frames, metrics, installer repair, assets and shutdown with
mocked device/Webots boundaries. New diagnostic checks verify raw physical
readings and explicit unavailable-measurement reporting without actuation.

It also verifies that `learn` rejects a static graph and `walk` rejects a plastic
graph before Webots launches. Direct controller entry performs the same check.
[APPLICATION_CHECK.json](APPLICATION_CHECK.json) records the result and hashes.

## Native circuit checks

[CASCADE_CHECK.json](CASCADE_CHECK.json) records eight fixtures using native CPU
neuron updates on the full static graph. Phase initialization, connectivity
sampling and fatigue handling are local harness assumptions; this is not the
complete device runtime or an equivalence test. No learning updates are simulated.

Ordinary fixtures make each foot airborne when neural knee flexion occurs and
supply landing after a minimum fixture interval with extension. They provide
sensory evidence only, without injecting turns or motor commands. This is not
a physics model of Spot. Harness steps are not milliseconds.

The checks cover two phase seeds, delayed landing, missing landing, no lift-off,
STOP/restart, left tilt and rear-right landing withheld until step 800:

- Ordinary fixtures repeat FR → RL → FL → RR → FR from one START.
- Missing landing and continuously planted contact retain the FR turn while
  its local motor primitive retries. Unqualified contact never ends the loop.
- In the rear-right fixture, flexion attempts occur at steps 403, 524, 644 and
  764. Qualified landing appears at 807; front-right starts at 829 without a
  second START. The completed RR loop stays off until its next request.
- No simultaneous active turns or opposed regular knee commands occur during
  exclusive WALK. The left-tilt fixture recruits FL/RL reflexes independently.
- STOP clears every local loop and retained motor/event state; restart begins
  at FR. Four fixtures show two frames of opposing knee readouts during the
  existing STOP settling transition, after WALK has cleared. These are recorded
  separately in the report; they are not counted as clean walking frames.

## Physical limits

The loop now retries until qualified contact. It cannot establish why contact
was missing: inadequate configured reach, load/torque limits, posture and support
geometry remain physical questions. Repeated neural attempts are not proof of
successful weight transfer. [PHYSICS.md](PHYSICS.md) explains the new read-only
center-of-mass, foot-center and motor-torque measurements.

KICK_DONE confirms neural kick output activity, not physical completion.
Actual timing, joint tracking, balance, dopamine activity, inhibitory weight
updates and learning improvement require runs on your Webots/Prima-Lux setup.
Simulator recovery is assistance and must be counted equally in comparisons.
Use [TESTING.md](TESTING.md) for the static-versus-learning procedure.
