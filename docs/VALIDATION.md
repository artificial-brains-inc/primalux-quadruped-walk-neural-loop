# Validation performed

- **82 local tests passed** using Python 3.12 and SDK 0.4.2.
- A fresh `bash install.sh` installed SDK 0.4.2 from PyPI and its dependencies;
  `pip check` reported no broken requirements. Webots was not installed.
- The public saved graph passes construction with the compatible 0.4.11 builder:
  598 total neurons, eight external input neurons, 110 populations, 391 connections
  and 568,736 bytes of connection matrices. Only aggregate feedback is included;
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
- Recovery checks cover a sustained fall, manual R, quiet motor outputs after REST,
  one robot reset, upright settling, one resumed START and cancellation with S.
  A reset from REST does not start walking. Recovery earns no positive reward;
  the session is stopped only on exit. Invalid readings, debounce, cooldown and
  recovery timeouts are tested separately. Reset displacement is excluded from
  reported physical displacement.
- Command tests cover delayed goal confirmation after ACK, ambiguous WALK/REST,
  stale frames, timeout reporting, replacing pending START with STOP and a new W
  press. After ACK, one native frame still produces one body step.
- The 64 ms body-advance check preserves one advance per native frame and obeys
  the next neural cutoff without a host completion latch. Launcher coverage checks
  rendered fast mode and confirmed shutdown. The supplied run's measured short
  target durations and body displacement are summarized in [Timing](../TIMING.md).
- SDK Design/Build/Run dispatch, actuator decoding, installer repair, world asset
  integrity and confirmed Stop/save remain covered.
- Python syntax/name checks and `git diff --check` passed. The published snapshot
  is packaged as a complete Git bundle that can update the prior learning package
  by fast-forward. A fresh clone
  was checked for graph identity, local assets, license and absence of credentials,
  virtual environments and private builder files.
- All 86 bundled Webots dependencies resolve locally and match their updated
  integrity manifest. Spot's five Camera devices are removed; its geometry,
  joints, masses, actuator settings and third-party licenses are preserved.
  The arena measures 30 × 30 metres with a local, noncollision FloorMarkings PROTO.
  Its generated grid/arrow/number meshes have valid face indices and floor heights.
  The wider opening viewpoint's rotation is checked
  mathematically against its target and an upright horizon; it has not been
  rendered in Webots here. World SHA-256:
  `d69785d541d8ee92f28bc20b2c79c008751d727d166e26be6ddc25c0d49d9373`.
- All 86 existing populations and 299 existing connections are preserved exactly.
  Four tilt input neurons and their independent static gamma reflex circuits are
  added. Each gamma/reset pair has two high-gamma T3 output adapters, required
  by the builder. ACTIVE has no outgoing paths, sensory paths have no inhibitory
  edges, and reflex targets cannot cross into another leg or phase. **Build is required**.
- An isolated gamma reflex check used native ARM cell updates with explicit
  phase initialization, sparse connectivity and coupling assumptions. Twelve
  cases varied initialization, coupling, membrane floor and input sample spacing.
  One- and two-cue stimulation produced bounded extension readouts; no activity
  appeared before stimulation or late after it ended. Observed bursts ranged
  from two to seven modeled steps. This excludes gait competition, STDP3,
  foot contact, body physics and device transport. It is not a compiled-image
  equivalence test or an optimized TNorm claim. See [REFLEX_CHECK.json](REFLEX_CHECK.json).
- Tests verify signed IMU encoding, atomic SDK publication, rejection handling,
  post-step evidence, unchanged motor decoding, and Stop/save after publication
  failure. Model geometry and ENU coordinate checks verify the knee extension
  and tilt-direction signs in the configured posture range. They do not establish
  that the foot reaches ground or that the body recovers balance.

These checks establish construction compatibility and adapter behavior. They do
not establish full-gait neural alternation, useful stepping, weight changes or
improvement due to STDP3. This revision has not been run on Prima-Lux/Webots here.
Gait inhibition strength 1, reflex inhibition strength 4, tilt deadband and reward
thresholds are initial settings for the live trial.
The device Build and the controlled trials in TESTING.md are still required.

The supplied physical trace describes the preceding reflex graph: 42 assisted
recoveries in about 323 wall seconds, with reflex ACTIVE readouts present but
not consistently accompanied by knee extension outputs. Its tilt publications
took about 78 ms at the median and 84 ms at the 95th percentile; the output queue
reached 92 frames. These observations motivate checking both local recruitment
and feedback latency. They do not establish saturation, dopamine firing, or the
performance of this revised graph.

```bash
python -m unittest discover -s tests -v
```
