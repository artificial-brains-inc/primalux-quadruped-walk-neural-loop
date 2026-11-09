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
`native-outputs.jsonl`, `commands.jsonl`, `tilt-inputs.jsonl`, `rewards.jsonl`,
`settings.json` and the run summary. Preserve a complete run when comparing
changes. The summary counts complete hip/knee patterns, all-four knee flexion,
and same-side-only knee flexion from actual motor outputs, separately from the
phase lamps. High queue depth means feedback can be stale relative to the device.

After static behavior is established, use `learn` to enable physical reward.
The four selected release inhibitory feedback paths and four regular support
phase drive → knee extension Beta paths are plastic, using LTD and LTP respectively. Every reflex connection
is static, including its direct excitation of regular Beta. Check presynaptic
support-drive activity alongside reflex and postsynaptic Beta activity; a reflex
burst alone does not establish eligibility on the regular connection.
Accepted reward publications alone do not establish dopamine firing or learning.
See [VALIDATION.md](VALIDATION.md) for the scope of the bundled check reports.

For the LTD experiment, compare against the corrected LTP design from commit
17918ee using matched initial weights, initial pose and run duration. Changing
`learn` to `walk` only suppresses external reward; it does not select LTP or LTD
or prove a frozen-weight baseline. Rebuild the intended design for each condition.
Record rearward hip movement overlapping the next leg's swing, forward progress,
falls and stalled intervals. Preserve the run settings and design hash. This
comparison tests release-feedback adaptation; the static A/B exclusion and
motor vetoes are not changed by the LTD selection.
