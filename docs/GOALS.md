# Build a goal by stating its evidence, action and exit

A goal needs an activation source, a retained state if the evidence is brief,
a motor consequence and an explicit way to stop. A goal interaction should say
what evidence authorizes the next goal and what clears the old one.

| Goal | Activation/evidence | Action | Exit/reset |
| --- | --- | --- | --- |
| Walk | One START event | Seed FR; enable the cascade | STOP/REST |
| One leg's turn | Its REQUEST | Recruit push, swing and return | Next turn's REQUEST/ACTIVE |
| Stance | START for the other three legs; next turn after own movement | Recruit regular support Betas | Own REQUEST/ACTIVE |
| Support plan | Previous RETURN; START seeds FR | Begin the next grounded push; apply small offsets away from that next foot | Next PREPARE, STOP/REST |
| Push | Local MOVE or own PREPARE | Small fast extension, available during STANCE | SWING_READY or DONE |
| Return | Local knee flexion output | Final extension; inhibit flexion | Stance, next request, STOP |
| Remember lift-off | Measured AIR while this turn is active | Retain AIR_SEEN | Request, stance, STOP |
| Landing | Measured CONTACT with AIR_SEEN and DONE | Retain CONTACT_READY | Request, stance, STOP |
| Handoff | CONTACT_READY opposed by local brake | Capture next REQUEST | Own stance/STOP |
| Reflex | Compatible signed tilt evidence | Fast extension and flexion inhibition | Local two-stage Beta reset; STOP |

The sequence specifies which leg follows which. Return activity prepares the
next movement; contact determines when its swing turn may proceed. The support
plan remains during that swing and is replaced when the following leg prepares. Learning is restricted to the inhibitory edge opposing
that permission; it neither invents contact nor changes the sequence.

Start by running the fixed circuit. If no foot leaves the floor, AIR_SEEN stays
zero and the first turn must hold. Inspect motor outputs, physical clearance and
raw contacts before changing learning. If AIR_SEEN is set but CONTACT_READY is
not, inspect measured landing and local DONE. If readiness is set but the next
request does not appear, inspect the two handoff Betas and inhibition.

Only after those causal steps work should reward influence the four local
handoffs. Compare actual progress and falls, not just faster switching.
