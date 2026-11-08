# Validation

SDK 0.4.2 accepts the saved design. The compatible local builder accepts its
construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json) records 503 total
neurons and 292,796 bytes of connection matrices; other image data also consumes
the 32 MiB budget. Device preparation remains authoritative.

96 application tests cover command/ACK/goal confirmation, SDK dispatch, motor
calibration, input encoding, reward, recovery, Stop/save, installer behavior,
assets, graph/source agreement and recording. Tests exercise push/fast/normal
outputs, conflicting commands and return to normal speed after clearing.

[SWITCH_CHECK.json](SWITCH_CHECK.json) records four complete-circuit local cases:
aligned initial phases, varied phases/coupling/floor, left tilt and right tilt.
The check injects START, STOP and tilt evidence, not phase or motor spikes. It
uses native ARM cell updates with explicit harness assumptions for initialization
and connectivity. Weights remain static. It is not the compiled device image,
an FPGA-equivalence test or a Webots physics run.

The checks measure push before knee flexion, local return-to-extension latency,
front support output at rear push and swing onset, phase exclusivity,
overlapping knee commands, reflex HG and
regular Beta activity, fast-output clearing, STOP and restart. A corrective
reflex can interrupt and delay an already prepared swing; the report preserves
those events instead of labeling every delayed swing a fresh preparation.

In these four local cases, KNEE_NEG became active one neural frame after DONE
on every recorded return. Front extension was already active at every rear
push onset. No simultaneous knee flexion/extension commands occurred. These
are harness observations, not a promise of the same timing on the device.

Local checks cannot resolve an observed model/device mismatch. Record actual
HG, Beta, reset, readiness and dopamine spikes through `neuron-telemetry.jsonl`.
Compare with targets, measured angles, tilt and body motion. Command readiness
and return do not prove foot contact or physical weight transfer. No ground
forces, stable walking or reward-driven weight changes have been validated here.

The supplied device run of the preceding graph showed front-right DONE at step
1528, rear-left PUSH at 1545 and normal front-right extension only at 1558:
a 30-frame / 0.96-second delay at the recorded 32 ms body step. Internal
telemetry showed the regular extension Beta first active at 1554. The new
direct return edges remove that serial dependency. The run used `learn` mode;
it is evidence of the observed delay, not a controlled static comparison or
validation of this updated graph on the device.

Run `walk` first. After the physical behavior works, compare `learn` against it
using progress, falls and weight observations. Supervisor recovery remains
explicit simulator assistance and is not learned self-righting.
