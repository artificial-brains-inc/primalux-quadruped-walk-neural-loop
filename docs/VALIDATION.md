# Validation and limits

The SDK 0.4.2 validator and compatible 0.4.11 construction builder accept both
supplied designs. They use **721 total neurons**, including **93 external
neurons**, across **253 populations** and **1,189 connections**. Dense connection
matrices use **331,828 bytes**; other prepared-image data also consumes memory.
[RESOURCE_CHECK.json](RESOURCE_CHECK.json) records the learning root's hash and
every population. The static companion has identical allocation and initial
strengths; it omits only the four learning annotations and has a different name.

Every previously existing population retains its constructed width. Motor
stroke targets/speeds, support offsets, reflex trigger/reset paths, contact gates, world,
foot-pad geometry and licenses are preserved. Each leg adds five neurons:
two for KICK_END_BETA T3, one KICK_DONE output, one HG T10 completion helper,
and one HG T10 flexion-wait helper. No external neurons are added.

## Application checks

**119 application checks are validated.** The application suite verifies graph construction contracts, exact inhibitory
plasticity placement, static/learning parity, SDK command dispatch, actual SDK
input encoding, controller frame handling, metrics, installer repair, assets
and shutdown with mocked device/Webots boundaries.

It also verifies that `learn` rejects a static graph and `walk` rejects a plastic
graph before Webots launches. Direct controller entry performs the same check.
[APPLICATION_CHECK.json](APPLICATION_CHECK.json) records the result and hashes.

## Native circuit checks

[CASCADE_CHECK.json](CASCADE_CHECK.json) records checks using native CPU neuron
updates on the full static graph. Phase initialization, connectivity sampling
and fatigue handling are local harness assumptions; this is not the complete
device runtime or an equivalence test. No learning updates are simulated.

Ordinary fixtures make each foot airborne when neural knee flexion occurs and
supply landing after a minimum fixture interval with extension. They provide
sensory evidence only, without injecting neural turns or motor commands. The
fixture is deliberately not a physics model of Spot.

Checks cover two phase seeds, delayed landing, missing landing, no lift-off,
STOP/restart and left tilt. They inspect sequence order, mutually exclusive
turns, antagonist outputs, bounded kicks, completion reset and STOP clearing.
The tilt fixture checks that existing independent left-side reflexes still fire.

A separately labelled fault fixture suppresses front-right KNEE_PUSH until
step 180 and drops its upstream MOVE/PREPARE recruitment after step 120. This
artificial perturbation tests recurrence: the local PUSH loop must persist
without falsely declaring completion, then terminate when the output is allowed
to fire. It is not evidence of physical actuator reliability.

## Limits to check on your setup

KICK_DONE confirms that the neural kick output fired, not that the foot moved,
unloaded or transferred weight successfully. Actual kick duration and contact
timing must be inspected on the device; harness steps are not milliseconds.
Missing physical touchdown still prevents the contact-qualified handoff.

Webots locomotion, actual dopamine firing, inhibitory weight updates and learned
improvement require runs on your setup. Automatic simulator recovery is
assistance and must be counted equally in both comparison conditions. Use
[TESTING.md](TESTING.md) for the static-versus-learning comparison.
