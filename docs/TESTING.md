# Test the circuit and then the learning claim

Build the saved design with SDK 0.4.2 and wait for READY. Set AB_TELEMETRY=true.
Keep the bundled world and `config.json` unchanged for initial comparisons.

## Check recruitment, release and STOP

1. Run `ab run -ab --env .env rhythm`. The actual brain runs while the body holds
   neutral targets and external reward stays zero.
2. Press W once. Check the separate key, command, ACK and goal-confirmation events.
   WALK=1 and REST=0 confirm the transition. Inspect START_REQUEST capturing the
   event, its helper carrying the request, and WALK_NUCLEUS clearing the request
   after takeover. Goal activity must persist without periodic external commands.
3. Follow A_T2 → A_INHIBITOR, A_BETA → A_RELEASE, and A_RELEASE inhibiting
   A_INHIBITOR. Inspect the mirrored B paths and the startup bias clearing.
4. Observe repeated cycles and all four leg groups. Look for both phases active,
   both blocked, a retained release state, or local POS/NEG overlap. Diagnostic
   outputs are bistable readouts, not the entire OPU's activity.
5. Press S and then W to test stopping and restarting. End with Q and wait for
   Stop/save confirmation. Startup STOP alone does not test stopping a gait.

If REST stays active, `commands.jsonl` distinguishes a missing W key event from a
command that was sent and ACKed but never confirmed. Inspect START_REQUEST and
STOP_REQUEST to locate capture or takeover failures. Learning does not repair a
failed command path; those paths are intentionally static. Keep the native trace
and inspect the actual WALK/REST competition instead of increasing reward.

## Measure physical outcome

Run `ab run -ab --env .env learn`, then W. The motor adapter consumes only local
motor outputs. Check the resulting joint/body measurements, not just A/B readouts.
The `reward` object in each observation explains why reward is 0 or 1.

Check that reward is absent during startup and pending commands, begins only for
qualifying forward movement, and clears on S. Use R for an assisted upright reset:
reward must stay zero through recovery and only restart after a fresh confirmed
START. Test S during recovery to cancel resuming. Disable `recovery.automatic` for
unassisted balance trials. Stop a run before manually dragging the robot or editing
the world: arbitrary drag displacement is not distinguished from physical motion.
Watch for upright sliding, rocking, asymmetric loading or falls. The first
reward deliberately uses one coarse outcome rather than many external neurons.

Compare reward timing with `queued_native_frames`. Body measurements follow the
applied neural frame; network delivery means the reward is consumed later. The
recorded native step is not a promise of same-step reward application. Excessive
backlog can damage credit assignment even when command ACK is working.

## Check the local support reflex

Run `learn` or `walk`, press W and correlate measured roll/pitch with the four
tilt bits, `REFLEX_*_ACTIVE` and each knee's POS/NEG outputs. Follow the
[reflex checks](REFLEX.md#observe-the-result): appropriate leg recruitment,
flexion veto, extension, self-clear and renewed response to later evidence.
Check S while a reflex is active; REST must silence it along with the gait.

The telemetry window shows actual neuron activity. Inspect `GAIT_REWARD_RELAY`
and `GAIT_REWARD` to verify dopamine firing; the accepted reward event log alone
does not establish this. Inspect the gamma reflex/reset pair and the MOTOR_HG
and CLEAR_HG adapters to separate input delivery, recruitment and cutoff failures.
ACTIVE is diagnostic only. Check simultaneous local responses: forward-left
evidence can recruit front-left, front-right and rear-left without any corner
veto. Do not expect a fixed burst length or infer saturation from ACTIVE alone.

Compare `reflex.enabled=true` with `false` in separate runs using otherwise
matched configuration and initial neural/body conditions. Record recovery count,
tilt, forward progress and knee movement. For this comparison a static graph
avoids ongoing learning as a confound; learned state must also be controlled.
Record the maximum output backlog and tilt publication duration: a fast neural
path does not eliminate body/network latency. Do not infer contact from a
negative knee target or call assisted resets neural recovery.

## Compare with a static graph

A zero external reward input is not proof that all internal reward/eligibility
activity vanished. To test a static baseline, stop the session and explicitly
author a graph with the learning metadata removed:

```bash
python design_brain.py --static
ab design --brain brain.abdesign.json --env .env
```

Close Designer, then:

```bash
ab device --env .env stop
ab build brain --brain brain.abdesign.json --env .env
ab run -ab --env .env learn
```

Using `learn` here still measures and logs exactly the same reward, but the graph
has no plastic connections. The static and learning designs retain identical
TNorms, topology, initial inhibitory strengths and external contracts.

To restore the learning design, stop and run:

```bash
python design_brain.py
ab design --brain brain.abdesign.json --env .env
```

Close Designer and repeat SDK Build, wait for READY, then Run. Both authoring
commands overwrite `brain.abdesign.json`; preserve Canvas edits first. The saved
resource report describes the shipped learning design, not subsequent edits.

Use comparable world reset conditions, configuration and episode lengths. Record
whether each run used a fresh installed brain or retained neural state; don't mix
those conditions in a learning comparison. Keep the logs from multiple trials.
Compare forward progress, reward fraction, body tilt, antagonist overlap, phase
handoff and STOP/restart. Improvement in one run is insufficient to attribute the
change to STDP3. Logs do not themselves prove that weights changed.

If the static circuit never generates usable movement, inspect neural recruitment
and actuator mapping first. An outcome reward supplies no missing trajectory or
exploration controller. There is no scripted motion fallback.
