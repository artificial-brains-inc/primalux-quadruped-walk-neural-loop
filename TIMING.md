# Motor duration and visible progress

The supplied run confirms that the short strokes are real. During 7,479
confirmed WALK frames (239.296 simulation seconds), Spot's world X position
advanced about 2.447 m and Y changed about -0.280 m. No recovery occurred in that
run, so this displacement was not caused by an upright reset. This measures body
displacement; it does not establish a coordinated walking gait or exclude sliding.

The hip targets changed before the joints arrived: only 6 of 223 non-neutral hip
target runs ended within 0.02 rad of their target. Typical hip/knee target runs
lasted five or six frames. At 32 ms per frame that allowed only 0.16–0.192 s.
The targets then returned to neutral, usually without a direct opposite command.
For example, a +0.35 rad front-left knee target lasted seven frames (0.224 s),
reached about +0.294 rad, then returned to zero. A +0.20 rad front-left hip target
lasted six frames (0.192 s), reached about +0.169 rad, then returned to zero.

The adapter now advances 64 ms per neural frame. The world's integration step
remains 16 ms: each native frame gets four physics substeps. The same five-frame
target therefore has 0.32 simulated seconds to act. Joint angles, servo speed
limits, torque limits, neural graph, learning rules and command/ACK protocol are
unchanged. A short or inhibited motor output still ends immediately at the next
native frame; the host does not latch a target until completion or generate a gait.

This is a calibration change, not a verified solution to all gait problems. In
the supplied run all 24 motor readouts were zero in 85.9% of confirmed WALK frames.
Doubling simulated time per frame does not eliminate those neural gaps or prove
that the phase circuit alternates correctly. The next run should establish
whether strokes complete more often and produce useful forward motion.

The run also accumulated as many as 323 queued native frames. The launcher now
uses Webots `--mode=fast` with normal rendering, removing realtime pacing. This
allows the body to consume queued frames faster when compute and reward delivery
permit. No output frames are dropped. Console `queued_frames` and summary
`maximum_queued_frames` expose remaining backlog. Fast mode alone does not
guarantee zero transport delay; sustained backlog also delays reward relative to
the device's current neural state. Keep that in mind when assessing learning.

Use the grid to assess movement: each small cell is 1 m, heavy lines are 5 m
apart, red arrows point along the initial forward direction (+X), and red labels
show metres from the blue start square. The camera follows Spot while the markings
stay fixed. The camera is farther away to show the feet and more floor.

For the next run, use W, watch several movement cycles, then Q and wait for
Stop/save. Inspect `joint_target_rad` against `joint_position_rad`, quiet motor
frames, queue depth and body displacement. Full strokes and useful walking still
need a live Webots/Prima-Lux test; local tests do not establish them.

Webots references:
- https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/robot.md
- https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/motor.md
- https://github.com/cyberbotics/webots/blob/R2025a/docs/guide/starting-webots.md
