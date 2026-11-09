# A local push, swing and return

Each leg retains its motor primitive. MOVE_HG recruits both its regular motor
Betas and PUSH_HG. The previous leg’s RETURN_BETA also recruits this leg’s
PREPARE_HG, which starts PUSH_HG while this leg is still in STANCE. STANCE no
longer vetoes the push relay/output; it still suppresses swing and local return.
SWING_READY and DONE retain their explicit push-clearing paths. PUSH directly excites KNEE_PUSH and inhibits knee flexion.
Its default target is −0.12 rad from neutral at up to 3 rad/s. This is intended
to shift weight before lift-off; useful physical weight transfer still needs
testing in Webots.

Hip Beta recruits SWING_READY, retained through its high-gamma helper.
SWING_READY_HG clears PUSH_HG and KNEE_PUSH at strength 64. It is not inhibited
by the push it must end. The normal flexion target is +0.35 rad at 1.5 rad/s.

Actual neural knee-flexion output recruits RETURN_BETA T3. RETURN directly
excites KNEE_NEG and inhibits KNEE_POS plus the local extension-output veto at
strength 64. It also sets retained DONE; DONE keeps final extension available,
ends MOVE/PUSH and recruits regular support Betas. Final extension is −0.08 rad
at 1.5 rad/s. There is no extra wait for the regular support Beta to produce its
output and no controller target-completion decision.

The preparation relay has two constructed neurons and the push relays have three neurons in front and four at the rear,
from its existing MOVE input plus the new preparation input. All regular motor
Betas, push target/speed and reflex populations retain their settings.

The next turn restores this leg's STANCE. Its next REQUEST clears old local
readiness and return state. The touch circuit must have observed lift-off and
landing before this leg hands off; DONE alone does not mean physical landing.
See [CONTACT.md](CONTACT.md).
