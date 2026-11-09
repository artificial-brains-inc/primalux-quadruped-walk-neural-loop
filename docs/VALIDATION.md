# Validation

SDK 0.4.2 accepts the saved design. The compatible local builder accepts its
construction. [RESOURCE_CHECK.json](RESOURCE_CHECK.json) records 503 total
neurons and 292,796 bytes of connection matrices; other image data also consumes
the 32 MiB budget. Device preparation remains authoritative.

98 application tests pass. They cover event commands without neural ACK, goal observation,
SDK dispatch, motor calibration, input encoding, reward, recovery, Stop/save,
installer behavior, assets, graph/source agreement and recording. Tests exercise
push/fast/normal outputs, conflicting commands and return to normal speed.

A blocked HTTP test delivers all 30 consecutive native motor frames while an
input request is stalled. Only the newest of 30 unsent captures is transmitted
after the request finishes. Other tests check command priority, in-flight request
shutdown and real SDK encoding of 48 tilt and 10 reward neurons in one frame.
Controller integration tests use a deterministic input sender; concurrent behavior
is tested separately with the real worker. These tests do not establish device
latency or stable Webots walking.

This experiment changes only four connection fields relative to the corrected
LTP design from commit 17918ee: reward_type becomes LTD on each RELEASE → its
own FEEDBACK_BETA and BETA inhibitory edge. The design name identifies the LTD
experiment. SDK validation and local construction pass. All nodes, connectivity
and constructed initial parameters remain identical; only the four reward
directions change. The regular support → extension Beta connections retain
STDP3/LTP. Every reflex edge remains static. The LTD experiment has not been run
on the device or in Webots and does not establish eligibility, more overlap or
improved behavior.

[SWITCH_CHECK.json](SWITCH_CHECK.json) retains the preceding design hash and
records four complete-circuit local cases with static weights:
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
