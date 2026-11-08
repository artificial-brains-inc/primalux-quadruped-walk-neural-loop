# Recovering after a fall

Focus the Webots 3D view and press **R**. Spot returns to the world's initial
upright pose at `(0, 0, 0.624)`, with its original joint positions and zero momentum.
If walking was requested, walking resumes after settling. If it was resting, it
stays in REST. **S** during recovery cancels the resume; **W** requests a resume.
**Q**, closing Webots and the normal terminal stop still end the neural session.

Automatic recovery is enabled in `config.json`:

```json
"recovery": {
  "automatic": true,
  "fall_tilt_rad": 1.05,
  "fall_height_m": 0.30,
  "fall_delay_seconds": 0.5,
  "settle_seconds": 1.0,
  "settle_timeout_seconds": 5.0,
  "stop_timeout_seconds": 5.0,
  "cooldown_seconds": 2.0
}
```

All durations above are simulation seconds. Tilt measures how far the body's up
axis tilts from world +Z. A sustained excessive tilt or low body triggers one
STOP request; a momentary wobble does not. Invalid sensor readings do not trigger
teleportation. Automatic recovery has a cooldown; R bypasses that cooldown.
Set `automatic` to `false` and restart the run to disable automatic intervention.

Recovery waits for the command's transport ACK, exclusive REST confirmation and
all 24 motor outputs to become quiet. The body continues one step per native
frame after ACK, using neutral targets during assistance. Only then does the
Webots Supervisor restore this robot with `loadState("__init__")` and
`resetPhysics()`. Motor speed settings are reapplied after state restoration.
Other objects, simulation time and the brain session continue. There is no neural
rebuild, device restart, weight reset, learned gait change or new external input.

Before resuming, Spot must remain within the existing upright reward thresholds
for `settle_seconds`: roll and pitch within 0.35 rad and body height at least
0.45 m with the shipped settings. If STOP or settling does not complete, the
session stops with an error instead of repeatedly issuing commands.

Reward is disarmed throughout recovery. A fresh confirmed START establishes a new
progress origin after settling; teleportation cannot earn reward. Observation logs
record `recovery_state`, `recovery_event` and `recovery_count`. The summary reports
recoveries and recovery frames; `displacement_xyz_m` sums only successive physical
observations outside recovery and omits reset jumps. It is net displacement, not
path length. Compare unassisted trials with automatic recovery disabled; assisted
episodes do not demonstrate balance or learned self-righting.

The world uses `supervisor TRUE` only for this explicit simulation assistance.
Its onboard cameras are removed; the main Webots Viewpoint remains. The viewpoint
starts at `(2.6, 2.6, 1.65)`, aims at `(0, 0, 0.45)` and uses Tracking Shot to follow
translation without rolling with the robot. The world and all its dependencies
remain local to the package.

Webots API references:
- https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/supervisor.md
- https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/viewpoint.md
