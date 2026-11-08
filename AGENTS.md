# Editing this example

Preserve the public design and input contract unless the user requests a change.
Use the Artificial Brains building guide's source-to-target relationships.

- External inputs are WALK_START, WALK_STOP, TRANSPORT_ACK and GAIT_REWARD_IN: one neuron each.
- Never send phase, gait-progress, oscillator or motor-output states back from
  Python as inputs. Internal populations connect directly in the brain.
- Physical outcome supplies one binary reward event from GPS/orientation after each qualifying body step.
  Never use reward measurement to choose a gait phase or actuator target.
- Keep STDP3/LTP on the 66 phase/release/motor veto paths. START, STOP, local
  antagonists, excitation and transport ACK stay static. Initial gait strength is
  1; command/REST clearing strength is 4. Do not treat TNorm as inhibitory intensity.
- Command clearing must touch command channels only; reward has its own publisher.
- Do not claim weight changes or better walking from construction or mocked tests.
- Keep shared Theta 3 → Theta 2.01 → Beta 5 preparation and local Beta 5 relays.
- A and B are phases. Preserve all four leg groups and 24 local motor populations.
- Each phase's INHIBITOR opposes the other phase. Its own downstream RELEASE
  inhibits that INHIBITOR, releasing the opposite phase. Preserve this topology.
- RELEASE does not directly clear its own motors. The opposite INHIBITOR does.
- WALK_DRIVE supplies both phases equally. A's inhibitor clears the startup bias.
- Live inputs are single-step events, not held levels. Capture START and STOP in
  neural request latches with high-gamma reinforcement. Success and opposite
  command cues clear both the request output and its helper. Never let REST block
  the initial START capture path or WALK block the initial STOP capture path.
- Reinforce WALK and REST internally, with explicit opposing command clear paths.
- Transport ACK is not goal confirmation. ACK zero and the post-confirmation idle snapshot are explicit hygiene events;
  they do not establish a held input. Observe exclusive WALK/REST confirmation.
- After ACK, keep stepping the body once per real neural frame while awaiting
  goal confirmation. Never republish periodic command stimuli or choose a phase.
- Use connection strength for inhibitory intensity; do not use TNorm as strength.
- Clear bistable outputs explicitly. Removing excitation alone is not a stop.
- The adapter decodes local actuator outputs only. No host gait clock, sine wave,
  IK gait, phase selector, periodic command refresh or hidden fallback movement.
- R and automatic fall recovery are explicit simulator assistance: request STOP,
  confirm REST and quiet motor outputs, restore this robot's initial state, hold
  neutral while settling, then issue one START if requested. Never reset the
  neural session, claim learned self-righting, or reward recovery movement.
- Keep SDK design/build/run steps separate. Install never installs Webots and
  never regenerates the saved graph.
- Keep credentials and private construction code out of the repository.
- A construction check or mocked runtime test does not prove neural dynamics or walking.
