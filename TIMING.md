# Neural timing and body timing

Each native output frame advances 64 ms of Webots simulation through four 16 ms
physics substeps. Fast mode removes realtime rendering pacing; no output frame
is deliberately dropped. Queue depth is logged. ACK waiting pauses physics;
after ACK, the body consumes neural frames while goal confirmation is pending.

The switch holds its state neurally. Four selected hip output neurons recruit
the handoff through high-gamma → Beta T5 → Beta T5 → release Beta T3. The release
captures the opposite request; its helper clears the old state and establishes
the new one. This is not a Python gait period or a promise of fixed milliseconds.

Local motor Betas and bistable outputs have propagation and clearing time. A
switch transition can include quiet or incomplete motor frames. The controller
applies those actual frames without extending a command until a target is reached.
When both antagonist outputs are zero, the configured neutral target is applied.

Each rear gait relay receives a front hip output (RR from FL, RL from FR), so
rear command recruitment follows front command activity. This adds neural
propagation, not a fixed millisecond delay or a guarantee of completed strokes.
Local reflexes remain direct and independent of these relays.

The fixed actuator calibration is separate: knee +0.35 / −0.08 rad, hip ±0.20 rad,
with a separate fast reflex knee target of −0.22 rad at up to 3.0 rad/s. Evaluate `joint_target_rad` against
`joint_position_rad` to see whether commanded strokes complete. Changing the
physics step changes how much simulated body time each neural frame receives;
it does not change a neural rhythm or transport ACK semantics.

The floor has 1 m cells and 5 m reference lines. Use those references and body
coordinates to distinguish forward progress from sliding or camera tracking.
Physical gait timing, stable contact and balance require the device/Webots run.
