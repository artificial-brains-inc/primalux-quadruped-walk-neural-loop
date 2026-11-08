# Validation

SDK 0.4.2 accepts the saved design. The compatible local builder accepts its
construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json) records 503 total
neurons and 291,900 bytes of connection matrices; other image data also consumes
the 32 MiB budget. Device preparation remains authoritative.

95 application tests cover command/ACK/goal confirmation, SDK dispatch, motor
calibration, input encoding, reward, recovery, Stop/save, installer behavior,
assets, graph/source agreement and recording. Tests exercise push/fast/normal
outputs, conflicting commands and return to normal speed after clearing.

[SWITCH_CHECK.json](SWITCH_CHECK.json) records four complete-circuit local cases:
aligned initial phases, varied phases/coupling/floor, left tilt and right tilt.
The check injects START, STOP and tilt evidence, not phase or motor spikes. It
uses native ARM cell updates with explicit harness assumptions for initialization
and connectivity. Weights remain static. It is not the compiled device image,
an FPGA-equivalence test or a Webots physics run.

The checks measure push before knee flexion, local return, front support output
at rear swing onset, phase exclusivity, overlapping knee commands, reflex HG and
regular Beta activity, fast-output clearing, STOP and restart. A corrective
reflex can interrupt and delay an already prepared swing; the report preserves
those events instead of labeling every delayed swing a fresh preparation.

Local checks cannot resolve an observed model/device mismatch. Record actual
HG, Beta, reset, readiness and dopamine spikes through `neuron-telemetry.jsonl`.
Compare with targets, measured angles, tilt and body motion. Command readiness
and return do not prove foot contact or physical weight transfer. No ground
forces, stable walking or reward-driven weight changes have been validated here.

Run `walk` first. After the physical behavior works, compare `learn` against it
using progress, falls and weight observations. Supervisor recovery remains
explicit simulator assistance and is not learned self-righting.
