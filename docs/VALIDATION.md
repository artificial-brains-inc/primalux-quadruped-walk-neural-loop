# Validation and limits

The SDK 0.4.2 design validator and compatible 0.4.11 construction builder accept
both supplied designs. They use **701 total neurons**, including **93 external
neurons**, **237 populations**, **1,105 connections** and **327,124 bytes** of dense
connection matrices. Other prepared-image data also consumes memory. The
allocation is comfortably below the 10,000-neuron /32 MiB budgets.
[RESOURCE_CHECK.json](RESOURCE_CHECK.json) records the static design hash and
every constructed population. The learning companion differs only in its name
and four inhibitory learning annotations; allocation and initial strengths match.

The 24 regular motor Beta populations and all reflex trigger/recovery population
widths match the preceding cascade. Existing stroke targets/speeds, world,
physical foot-pad geometry and licenses are preserved. Four new preparation
relays have two neurons each. Their added input makes the front push relays
three neurons and the rear push relays four. Sixteen new motor outputs add
fixed HIP/ABD support offsets. There are no added external input neurons.

The support direction was checked against the bundled leg geometry near the
standing pose. This verifies joint signs only, not center-of-mass position,
contact loads or physical stability. Offsets remain provisional calibration.

## Application checks

**114 application tests pass.** The application suite covers the graph's turn order, liftoff/return/contact gates,
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

At initial inhibition 0.5, nine full-graph fixtures cover two phase seeds,
standing, missing lift-off, missing landing, wrong-foot evidence, delayed landing,
STOP/restart and left tilt:

- One START produces FR → RL → FL → RR repeatedly. No simultaneous ACTIVE
  turns or opposed knee outputs occur during exclusive WALK in these fixtures.
- The next grounded push appears before measured touchdown in the ordinary and
  delayed-landing fixtures. With the short 18-step fixture this lead can be only
  one harness step. The lead grows when the synthetic landing is delayed; there
  is no fixed lead-time guarantee or conversion to physical milliseconds.
- No support-offset outputs coincide with that leg’s neural knee-flexion output
  during exclusive WALK in these checks. This is output-level exclusion, not
  measured foot unloading.
- Missing lift-off, missing landing and wrong-foot evidence each hold the first
  turn. A missing landing can leave the next preparation/push held; it does not
  start the next swing. STOP clears it.
- STOP clears movement and support plans; restart seeds FR again.
- Left tilt still recruits FL/RL fast reflex outputs while FR/RR stay quiet.

[HANDOFF_SWEEP.json](HANDOFF_SWEEP.json) tests fixed multipliers 0.5, 1 and 2
on this graph. First contact readiness is step171; next ACTIVE is185,187 and199
respectively. This confirms that the original inhibitory timing path still has
an effect. These checks do not train STDP3 or demonstrate improvement from reward.

## Still to test on your setup

Webots physics, foot unloading and weight transfer; device phase/synapse behavior;
transport sampling of brief lift-off; retained-state and checkpoint behavior;
actual dopamine firing, inhibitory weight updates and repeated-trial locomotion
improvement. Automatic simulator recovery must be reported as assistance in both
conditions. Use [TESTING.md](TESTING.md) to compare the static and learning runs.
