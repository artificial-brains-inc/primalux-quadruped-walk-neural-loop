# Building goals and choosing their interactions

A goal needs activating evidence, a way to retain activity when needed, an
output that expresses it, and conditions that end or oppose it. Define these
relationships before selecting rhythms and TNorms.

## WALK and REST

A brief START event recruits a retained request. That request activates WALK
and opposes REST. WALK reinforces itself and clears the request. STOP uses the
same pattern in the opposite direction. REST clears movement and motor outputs.
Goal confirmation is observed from WALK/REST while motor delivery continues.
No transport ACK is stimulated or awaited.

## Prepare, move and return

The early push is a local motor goal. It receives the same movement request as
the normal motor pathway, but reaches extension directly through high-gamma.
It opposes knee flexion output while the ordinary hip Beta builds activity.
That Beta recruits a retained readiness state which ends the push. Retention
keeps the push from restarting in a gap between Beta spikes.

Actual knee flexion output then recruits a return pathway. Its Beta directly
excites final extension and clears flexion and the extension-output veto. The
retained return state continues those paths while the regular support Beta
builds activity. A local contact veto blocks handoff until measured contact
qualifies that return. CONTACT_READY then recruits the diagonal rear partner
for a front leg, or the opposite macro state for a rear leg. A runs FR then RL,
B runs FL then RR. Python supplies four raw contact signals, with no phase,
cadence or handoff decision. The learned outcome remains upright progress.

This separates two goals: extend the foot toward support, then hand off when
contact is observed. Waiting for contact must not inhibit the extension needed
to achieve it. CONTACT_READY retains the event through brief later contact gaps
and clears during local MOVE or the opposite phase. See [CONTACT.md](CONTACT.md).

## Local corrective priority

Tilt evidence recruits the affected leg's high-gamma T5 reflex. It directly
excites fast extension and the existing regular extension Beta, while inhibiting
local flexion Beta/output and the local extension-output veto. It does not ask
another leg to stop or select a new macro state. Fast output recruits two Beta
T3 recovery stages which clear that output and its trigger neurally.

The normal extension Beta remains available to reflex evidence during swing;
the gait veto acts on its output. This separates receiving evidence from
expressing a motor command. The fixed direct reflex output remains available.

## Decide what can adapt

Static dynamics establish command retention, push, sequencing, competition and
reflexes. Only four STDP3/LTP inhibitory returns can adjust macro release
recovery: each phase's RELEASE inhibits its own FEEDBACK_BETA and BETA through
these plastic paths. All other connections remain static. In particular,
support phase drive → regular extension Beta and both reflex branches stay
fixed. The reflex still recruits the regular Beta, but that excitation has
no learning rule.

Reward is new upright forward progress, not merely reflex activation. Accepted
reward input is not proof of dopamine spikes, weight changes or improved walking.
First observe working behavior in `walk`, then evaluate adaptation in `learn`.
