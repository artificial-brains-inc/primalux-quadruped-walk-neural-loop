# Validation and limits

The saved graph passes construction with the compatible 0.4.11 builder:
**922 total neurons**, including 52 external neurons, 108 populations and
385 connections. Connection matrices occupy 1,123,584 bytes, approximately
1.07 MiB. Other image data also uses the 32 MiB budget. The device Build remains
authoritative. Only aggregate feedback is distributed; private construction
code and compiled neural images are excluded.

## SDK and application checks

**83 local tests passed** with Python 3.12 and SDK 0.4.2. They cover:

- Matching saved design and adapter contracts: eight named inputs, four tilt
  vectors of twelve bits, and the unchanged forty one-neuron outputs.
- Native SDK encoding and atomic transmission of all 48 tilt neurons; complete
  clearing during recovery/shutdown and isolation from command/reward channels.
- High-gamma T3 excitation of the extension Beta, with no direct reflex
  excitation of a motor output; inhibition of both the flexion Beta and output.
- Compatible high-gamma sources at each extension Beta, local reflex feedback,
  reset recruitment by the extension Beta, and preserved motor-clearing paths.
- No reflex connections to another leg or shared phase; no ACTIVE feedback or
  guard. Every population has an input-anchored construction path.
- All 66 STDP3/LTP gait inhibitory connections. Eight knee-extension connections
  originate from local veto relays; reflex excitation, self-reset and reflex
  inhibition remain static. The static comparison changes learning metadata only.
- START/STOP request capture and retention, delayed goal confirmation after ACK,
  one body advance per native frame, and no periodic command resends.
- Outcome reward eligibility, no reward during assisted recovery, manual and
  automatic recovery, STOP during recovery, and confirmed Stop/save on exit or
  publication failure. The adapter never converts reflex diagnostics into motion.
- SDK Design/Build/Run dispatch, installer repair, actuator decoding, world
  asset integrity and local model conventions.

The command nucleus is unchanged. Its separate isolated check completed
36 START/STOP/restart transitions across six initialization cases; see
[COMMAND_CHECK.json](COMMAND_CHECK.json). That check does not execute the gait.

## Local neural interaction check

[REFLEX_CHECK.json](REFLEX_CHECK.json) describes a local front-left circuit
using the saved graph's constructed connections and native ARM cell updates.
The checked circuit includes both motor Betas, both motor outputs, the reflex,
its reset, the local extension-veto relay and the shared phase-drive relays.

Eight cases impose competing flexion-phase activity while supplying one or two
tilt cues at different sample intervals. They vary initialization and explicit
coupling/membrane-floor assumptions. The checked behavior is extension Beta/output
recruitment, flexion Beta/output suppression, cessation of the reflex when cues
end, return of flexion, and silence under REST. A separate single-event check
verifies that local feedback does not remain active indefinitely.

These are bounded local checks, not compiled-image equivalence or an execution
of the complete rhythmic gait. Initial states, sparse connectivity, phase
coupling and upstream activity are explicit assumptions. Learning-induced weight
changes, transport latency, body physics, contact and servo completion are not
simulated. T3 and the selected inhibitory strengths remain settings for the live
trial, not universal prescriptions or demonstrated optima.

## Package checks

Python syntax/name checks and `git diff --check` passed. The complete Git bundle
contains a checkoutable HEAD and can fast-forward the previous local-reflex
package. A fresh clone was checked for saved-design identity, local assets,
license files and absence of credentials, environments, logs and private tools.

All 86 Webots dependencies resolve locally and match their integrity manifest.
The 30 × 30 metre grid world, initial view, camera removal, mechanical model,
64 ms body advance and actuator settings are unchanged. Webots is installed
separately and is never installed by this package.

This revision has not been run on Prima-Lux/Webots here. The checks do not prove
stable walking, successful balance recovery, dopamine firing or improvement
from learning. Use the comparisons in [TESTING.md](TESTING.md), inspect actual
neuron activity and correlate it with knee and body motion.

```bash
python -m unittest discover -s tests -v
```
