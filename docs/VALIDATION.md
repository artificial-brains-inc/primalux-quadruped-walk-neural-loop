# Validation

The saved design is generated through SDK 0.4.2 public fields. The compatible
0.4.11 builder accepts its construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json)
records the design hash, 520 total neurons and 414,400 bytes of matrix storage.
Other prepared-image data also uses the 32 MiB image budget.

Application tests cover command/ACK/goal confirmation, SDK dispatch, local motor
decoding, tilt encoding, reward evidence, Stop/save, recovery, installer behavior,
asset resolution, graph/source agreement and the new I/O contract.

[SWITCH_CHECK.json](SWITCH_CHECK.json) records the complete-circuit local check.
All neural populations run; only START, STOP and physical tilt evidence are
injected. Phase activity and motor spikes are not imposed by the test. The check
uses native ARM cell updates with explicit initialization, adjacency, coupling
and membrane-floor assumptions. It is not the device's compiled image or an
FPGA-equivalence test. Connections remain static during this check.

The report includes both exclusive switch states, alternations, complete knee
patterns, transition gaps, all-four-flexion occurrences, local reflex overrides,
stop clearing and restart. A motor output is a command, not ground contact.
The tests do not include Webots physics, device transport timing, dopamine-driven
weight changes, physical stability or proof of learned walking.

Use `walk` first, with reward disabled and reflexes enabled. Compare state
readouts with actual hip/knee outputs and joint positions. Then enable `learn`
and compare physical progress, falls and observed changes on the selected paths.
