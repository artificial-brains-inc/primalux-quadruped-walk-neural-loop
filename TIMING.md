# Neural timing and body timing

Each native output frame advances 32 ms of Webots time through two 16 ms physics
substeps. Fast mode removes realtime rendering pacing; no output frame is
deliberately dropped. Queue depth is logged. There is no neural ACK handshake.
START/STOP publication and sensor publication run on one separate worker, so
HTTP latency does not block the motor loop. WALK/REST confirmation is observed
while every native output frame continues through actuation.

The worker retains one latest unsent feedback capture, not a queue of old tilt
contact and reward readings. All are encoded in one atomic public SDK input frame.
A request already in flight cannot be replaced; network and device latency still
exist. Logs record capture age, publication duration and replaced unsent samples.
The dormant isolated ACK nodes remain inactive. The cascade adds local
contact/air event gates and changes the I/O contract, so it requires a build. It does not
add a host gait timer, output hold, ACK or change the motor calibration.

Local MOVE_HG recruits an early push alongside the existing motor Betas. Hip
Beta activity recruits retained readiness, which clears the push. Knee flexion
output recruits RETURN_BETA, which directly requests final extension and clears
flexion and the local output veto. DONE_HG retains those commands. This avoids
waiting for an additional support Beta before landing. Each local return pathway
authorizes contact only after this turn has observed lift-off. Qualified landing
recruits the next local stage through the handoff Beta and its inhibitory brake. These paths add neural integration
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
time per neural frame; it does not change neural rhythms.

The floor has 1 m cells and 5 m reference lines. Assess body displacement rather
than camera motion. Neural readiness and return do not establish unloading,
ground contact, physical balance or successful weight transfer.
