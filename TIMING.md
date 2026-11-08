# Neural timing and body timing

Each native output frame advances 32 ms of Webots time through two 16 ms physics
substeps. Fast mode removes realtime rendering pacing; no output frame is
deliberately dropped. Queue depth is logged. ACK waiting pauses physics; after
ACK the body consumes neural frames while goal confirmation is pending.

Local MOVE_HG recruits an early push alongside the existing motor Betas. Hip
Beta activity recruits retained readiness, which clears the push. Knee flexion
output recruits the return. A front return pathway recruits its rear partner;
a rear return recruits the macro handoff. These paths add neural integration
and propagation, not a prescribed millisecond schedule.

The reflex has a fixed direct HG motor branch. Its fast output recruits two
Beta T3 stages before clearing itself and its trigger. The body receives that
output directly; there is no host burst timer or wait-until-target rule. When
all local motor outputs are zero, the configured neutral target is applied.

| Motion | Knee excursion | Speed limit |
| --- | --- | --- |
| Normal flexion / extension | +0.35 / −0.08 rad | 1.5 rad/s |
| Early push | −0.12 rad | 3.0 rad/s |
| Corrective reflex | −0.22 rad | 3.0 rad/s |

Speed is capped by the model. Tilt publication starts beyond 0.08 rad. Compare
`joint_target_rad`, `joint_speed_limit_rad_s` and `joint_position_rad`: a command
is not proof that a stroke finished. Changing body step changes simulated body
time per neural frame; it does not change neural rhythms or ACK semantics.

The floor has 1 m cells and 5 m reference lines. Assess body displacement rather
than camera motion. Neural readiness and return do not establish unloading,
ground contact, physical balance or successful weight transfer.
