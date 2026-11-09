# Testing the switch

Activate the installed environment, then run the application checks:

```bash
python -m unittest discover -s tests -v
```

Inspect and build the saved graph with the SDK, then begin with:

```bash
ab run -ab --env .env walk
```

Focus the 3D view and press W once. Observe several cycles. A should support
FL/RR while FR/RL swing; B should exchange the roles. Check hip movement together
with knee flexion. Inspect transition gaps and actual joint travel, not only the
phase lamps. S should stop; W should restart; Q should stop and save. Closing
Webots must also stop/save. R and automatic recovery are simulator assistance.

Keep the reflex enabled. A tilt should recruit local extension and suppress
local flexion without selecting a global phase. Each signed cue can support two
legs. Simultaneous roll/pitch cues can recruit three; that is intentional
independent wiring rather than a single selected corner.

Logs are written under the configured run directory: `observations.jsonl`,
`native-outputs.jsonl`, `commands.jsonl`, `tilt-inputs.jsonl`, `contact-inputs.jsonl`, `rewards.jsonl`,
`settings.json` and the run summary. Preserve a complete run when comparing
changes. The summary counts complete hip/knee patterns, all-four knee flexion,
and same-side-only knee flexion from actual motor outputs, separately from the
phase lamps. High queue depth means feedback can be stale relative to the device.

First inspect `contacts` and `contact_ready` in the console. Standing feet
should report contact; a raised pad should report zero. Compare raw foot contact,
CONTACT_VETO_HG, CONTACT_MATCH_HG, CONTACT_READY and the downstream handoff in
telemetry. DONE can be active while CONTACT_READY is still zero: the return is
commanded but contact has not yet qualified it. Do not bypass that condition
with a controller phase change. See [CONTACT.md](CONTACT.md).

Check same-side overlap next. RL_HIP_NEG should recruit FL_HIP_POS through
LEG_FL_STANCE_HANDOFF_HG; RR_HIP_NEG should recruit FR_HIP_POS through its relay.
Follow actual output onsets and measured hip motion together. Rear knee landing
must still work before the hip handoff, and front DONE must suppress the relay
while the rear stance is held. Stop and restart to verify both output clearers.
See [SAME_SIDE.md](SAME_SIDE.md) for the exact static paths.

After static behavior is established, use `learn` to enable physical reward.
Only the four selected inhibitory release-feedback paths are plastic, using
STDP3/LTP. Every excitatory connection and every reflex/contact path is static.
Check RELEASE activity alongside its own FEEDBACK_BETA and BETA, the reward
neurons and the weights of those four inhibitory connections.
Accepted reward publications alone do not establish dopamine firing or learning.
See [VALIDATION.md](VALIDATION.md) for the scope of the bundled check reports.

For a controlled learning comparison, use this corrected physical model in both
conditions. Run `python design_brain.py --static`, inspect and build it for a
nonplastic baseline. Then regenerate with `python design_brain.py`, inspect and
build the inhibitory LTP design. Keep initial pose and run duration matched. Changing
`learn` to `walk` only suppresses external reward; it does not remove plasticity
or prove a frozen-weight baseline. Record forward progress, falls, stalls and
foot-contact events. Preserve settings and the design hash for both conditions.
