# Validation and limits

The SDK 0.4.2 design validator and compatible 0.4.11 construction builder accept
both supplied designs. They use **665 total neurons**, including **93 external
neurons**, **213 populations**, **960 connections** and **317,520 bytes** of dense
connection matrices. Other prepared-image data also consumes memory. The
allocation is comfortably below the 10,000-neuron /32 MiB budgets.
[RESOURCE_CHECK.json](RESOURCE_CHECK.json) records the static design hash and
every constructed population. The learning companion differs only in its name
and four inhibitory learning annotations; allocation and initial strengths match.

The 24 regular motor Beta populations and all reflex trigger/recovery population
widths were compared with the working pre-contact motor design. They match.
Local motor rhythms/TNorms, configured joint targets/speeds, world, physical
foot-pad geometry, tilt reflexes and license files are preserved. The shared
A/B selector is replaced by four retained local turns and contact-event memory.
No additional motor relay shortcut or controller gait rule is introduced.

## Application checks

**111 application tests pass.** The application suite covers the graph's turn order, liftoff/return/contact gates,
local brake placement, static/learning parity, exact input/output contracts,
actual SDK encoding, explicit design/build/run command dispatch, asynchronous
sensor publication, motor frame preservation, metrics and shutdown. Installer
checks include pip repair. Asset checks verify relative dependencies, physical
foot-pad colliders, marked floor, view and absence of onboard cameras.

These are automated application checks with mocked device/Webots boundaries.
They do not establish that a physical step completes successfully.

## Native circuit checks

[CASCADE_CHECK.json](CASCADE_CHECK.json) records checks on the full constructed
static graph with native CPU cell updates. Phase initialization, connectivity
sampling and fatigue handling are local harness assumptions; this is not the
complete device runtime. A synthetic contact fixture becomes airborne when
neural flexion occurs and lands after a minimum fixture interval when extension
occurs. It supplies sensory evidence only; it never forces a neural turn or
motor output. This fixture is deliberately not a physics model of Spot.

At initial inhibition 0.5:

- One START produces FR → RL → FL → RR and repeats in two initial phase seeds.
  No simultaneous turn outputs occur in the sampled frames.
- Continuous planted contact, missing landing and movement of the wrong foot
  each prevent premature handoff. Standing without START recruits no turn.
- STOP clears movement; a subsequent START begins again with FR.
- Left tilt recruits the FL and RL fast reflex outputs while FR/RR stay quiet.
- No opposed knee outputs occur during exclusive WALK in these fixtures.
  The restart fixture has two opposed knee-output frames during its final STOP
  transition with REST active. All motor outputs then clear. The unchanged
  adapter cancels opposing commands; this is a transient to inspect on the device,
  not a claim of instantaneous neural stopping.

[HANDOFF_SWEEP.json](HANDOFF_SWEEP.json) varies only the four fixed inhibitory
multipliers. The brake fires before qualified landing and a stronger setting
changes the time of the next turn. The selected 0.5 is a provisional responsive
baseline. The sweep does not train STDP3, optimize gait or demonstrate benefit
from reward. Do not convert its harness steps directly to milliseconds.

## Still to test on your setup

Webots physics, foot unloading and weight transfer; device phase/synapse behavior;
transport sampling of brief lift-off; retained-state and checkpoint behavior;
actual dopamine firing, inhibitory weight updates and repeated-trial locomotion
improvement. Automatic simulator recovery must be reported as assistance in both
conditions. Use [TESTING.md](TESTING.md) to compare the static and learning runs.
