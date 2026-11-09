# Compare a fixed circuit with inhibitory learning

Use the exact SDK inspect/build/run steps in the README. The two supplied
designs differ only in their name and four learning annotations. Their initial
strength is 0.5 on the same BRAKE_BETA → HANDOFF_BETA edges. Changing files does
not change the installed brain: explicitly rebuild each condition.

1. Select `designs/static.abdesign.json`, build it, and run `walk`. Confirm one W
   produces FR → RL → FL → RR repeatedly and S stops it. Check physical foot
   clearance and progression on the marked floor. If it cannot complete a cycle,
   fix the static motor/contact behavior before evaluating learning.
2. Save the run directory. Use a chosen simulation duration (for example ten
   minutes) and press Q yourself; the program imposes no time limit.
3. Select `designs/learning.abdesign.json`, build from the same initial design,
   and run `learn` from the same initial world. Use the same chosen simulation
   duration, motor/reflex settings, terrain and recovery configuration.
4. Compare the two log directories. Repeat fresh-build trials; one pair can be
   affected by contact variability. Record whether a device checkpoint was
   resumed rather than assuming saved weights were reset. A fresh design build
   is the intended common starting condition, not a request to reuse learned state.

```bash
python compare_runs.py logs/run-STATIC_DIRECTORY logs/run-LEARNING_DIRECTORY
```

Check normalized forward progress, recoveries per walking minute, sequence errors,
landing-to-next-stage delays, tilt and antagonist overlap. Recovery teleportation
is excluded from displacement. The reward high-water mark is episode-specific,
so it must not be treated as total distance across several recoveries.

`settings.json` records each design hash, mode, four initial strengths and actual
plastic metadata. `rewards.jsonl` shows accepted reward delivery; neuron telemetry
shows whether GAIT_REWARD fired. Neither alone proves a weight update. If weight
inspection is unavailable, label results behavioral improvement rather than
claiming a measured synaptic change.

Use `rhythm` only for a stationary circuit diagnostic. It does not actuate the
legs and supplies real standing contacts, so this contact-dependent cascade is
expected to hold rather than run freely without observed lift-off.

## Application checks

From a fresh checkout after install:

```bash
python -m unittest discover -s tests -v
```

These check graph contracts, static/learning parity, SDK encoding and commands,
contact validation, local motor/reflex paths, async publication, no ACK pacing,
metrics, installer repair and shutdown. They do not contact a real Prima-Lux
or start Webots. [VALIDATION.md](VALIDATION.md) separates these from native-cell
checks and the physical test still required.

## Check anticipatory support first

Use the static design. In observations.jsonl, compare the previous leg’s return,
next PREPARE and next KNEE_PUSH with the measured touchdown. Preparation should
be recruited during return, while next ACTIVE still waits for qualified landing.
Inspect `next_push_before_previous_touchdown_frames`, support motor outputs and
body pitch/roll together. Neural overlap alone is not successful weight transfer.
Confirm STOP clears PREPARE and support outputs and that START restarts FR.
The two optional support offsets can be set to zero for an amplitude-only
comparison; keep all other config values and the design identical.
