# Validation performed

- **58 local tests passed** using Python 3.12 and SDK 0.4.2.
- A fresh `bash install.sh` installed SDK 0.4.2 from PyPI and its dependencies;
  `pip check` reported no broken requirements. Webots was not installed.
- The public saved graph passes construction with the compatible 0.4.11 builder:
  542 total neurons, four external input neurons, 86 populations, 299 connections
  and 553,056 bytes of connection matrices. Only aggregate feedback is included;
  no private construction code or compiled neural image is distributed.
- The original command circuit's REST lock was reproduced in an isolated local
  check using the native ARM neuron-update source with one-step input events.
  The corrected request latches completed 36 START/STOP/restart transitions across
  six initial-condition cases and then cleared their request readouts. The check
  did not execute the rhythmic gait or Webots physics and is not an FPGA test.
  See [aggregate command results](COMMAND_CHECK.json); no private simulation or
  construction source is included.
- Graph tests check unopposed request capture, request reinforcement, success and
  opposite-cue clearing, all four leg groups, preserved phase/TNorm relationships,
  complete STDP3 coverage of the 66 gait inhibitory paths, and static command,
  STOP and ACK paths. The static comparison keeps topology and initial strengths.
- Tests exercise the installed SDK's reward encoder and named-input transport.
  One reward neuron encodes 0/1; command clears never overwrite that input.
- Reward tests distinguish new forward progress from stationary, backward,
  sideways, retracing, low and tilted motion. Invalid measurements and reset
  simulation time disarm reward. Each qualifying physical observation publishes a reward event; a previous 1 is
  not assumed to remain active.
- Mocked Webots/SDK integration checks reward after completed body steps and only
  after START confirmation, reward clearing on STOP, no positive reward in walk
  or rhythm modes, and SDK Stop even when reward clearing fails.
- Command tests cover delayed goal confirmation after ACK, ambiguous WALK/REST,
  stale frames, timeout reporting, replacing pending START with STOP and a new W
  press. After ACK, one native frame still produces one body step.
- SDK Design/Build/Run dispatch, actuator decoding, installer repair, world asset
  integrity and confirmed Stop/save remain covered.
- Python syntax/name checks and `git diff --check` passed. The published snapshot
  is packaged as a complete Git bundle that can update the prior learning package
  by fast-forward. A fresh clone
  was checked for graph identity, local assets, license and absence of credentials,
  virtual environments and private builder files.
- All 86 bundled Webots dependencies, the world, actuator settings and licenses
  are preserved. World SHA-256:
  `4435a1c45b68984c1de370d465dd644c700f94096808d994b3790db420a460c3`.

These checks establish construction compatibility and adapter behavior. They do
not establish full-gait neural alternation, useful stepping, weight changes or
improvement due to STDP3. No live Prima-Lux or Webots run was available here.
Inhibition strength 1 and the reward thresholds are initial experimental settings.
The device Build and the controlled trials in TESTING.md are still required.

```bash
python -m unittest discover -s tests -v
```
