# A local push, swing and return

Each leg retains its motor primitive. MOVE_HG recruits both its regular motor
Betas and PUSH_HG. PUSH directly excites KNEE_PUSH and inhibits knee flexion.
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

The next turn restores this leg's STANCE. Its next REQUEST clears old local
readiness and return state. The touch circuit must have observed lift-off and
landing before this leg hands off; DONE alone does not mean physical landing.
See [CONTACT.md](CONTACT.md).
