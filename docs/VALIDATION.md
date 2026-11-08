# Validation performed

- **57 local tests passed** using Python 3.12 and SDK 0.4.2.
- A fresh `bash install.sh` installed SDK 0.4.2 from PyPI and its dependencies;
  `pip check` reported no broken requirements. Webots was not installed.
- The public saved graph passes construction with the compatible 0.4.11 builder:
  538 total neurons, four external input neurons, 82 populations, 285 connections
  and 552,664 bytes of connection matrices. Only aggregate feedback is included;
  no private construction code or compiled neural image is distributed.
- Graph tests check all four leg groups, preserved phase/TNorm relationships,
  complete STDP3 coverage of the 66 gait inhibitory paths, and static command,
  STOP and ACK paths. The static comparison keeps topology and initial strengths.
- Tests exercise the installed SDK's reward encoder and named-input transport.
  One reward neuron encodes 0/1; command clears never overwrite that input.
- Reward tests distinguish new forward progress from stationary, backward,
  sideways, retracing, low and tilted motion. Invalid measurements and reset
  simulation time disarm reward. Only binary transitions are published.
- Mocked Webots/SDK integration checks reward after completed body steps and only
  after START confirmation, reward clearing on STOP, no positive reward in walk
  or rhythm modes, and SDK Stop even when reward clearing fails.
- Command tests cover delayed goal confirmation after ACK, ambiguous WALK/REST,
  stale frames, timeout reporting, replacing pending START with STOP and a new W
  press. After ACK, one native frame still produces one body step.
- SDK Design/Build/Run dispatch, actuator decoding, installer repair, world asset
  integrity and confirmed Stop/save remain covered.
- Python syntax/name checks and `git diff --check` passed. The published snapshot
  is packaged as a complete Git bundle with a single initial commit. A fresh clone
  was checked for graph identity, local assets, license and absence of credentials,
  virtual environments and private builder files.
- All 86 bundled Webots dependencies, the world, actuator settings and licenses
  are preserved. World SHA-256:
  `4435a1c45b68984c1de370d465dd644c700f94096808d994b3790db420a460c3`.

These checks establish construction compatibility and adapter behavior. They do
not establish sustained neural alternation, useful stepping, weight changes or
improvement due to STDP3. No live Prima-Lux or Webots run was available here.
Inhibition strength 1 and the reward thresholds are initial experimental settings.
The device Build and the controlled trials in TESTING.md are still required.

```bash
python -m unittest discover -s tests -v
```
