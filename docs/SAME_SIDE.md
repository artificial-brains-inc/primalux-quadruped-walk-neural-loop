# Contact changes the switch

The next movement begins because measured contact advances the neural sequence.
The controller reads each bumper and transmits its four-neuron input; it does
not select a leg, request a phase change or wait on a movement timer.

| Current state | Contact during local return | Result |
| --- | --- | --- |
| A | Front right | Start rear-left movement within A |
| A | Rear left | Change to B; start rear-left support and front-left movement |
| B | Front left | Start rear-right movement within B |
| B | Rear right | Change to A; start rear-right support and front-right movement |

W seeds A for the first front-right movement. Each leg still performs its local
push, flexion/advance and final extension. The sensor supplies positive evidence
to its CONTACT_MATCH_HG. Local return activity removes the veto that otherwise
blocks that evidence. CONTACT_READY captures it for the handoff.

For a rear foot, CONTACT_READY_HG recruits the current phase's FEEDBACK_BETA T5,
which requests the opposite phase. The switch does not wait for the later
BETA T5 and RELEASE T3 stages: those continue as the reset branch. The opposite
phase clears the previous OUT/DRIVE, while allowing its reset branch to finish.

The new phase recruits rear hip support and the same-side front MOVE_HG through
their normal motor paths. There is no rear HIP_NEG → front HIP_POS shortcut.
Rear landing retains its forward hip output until support starts, and its final
knee extension remains available while contact is missing.

All contact, switch recruitment and excitatory motor edges are static. Only four
RELEASE inhibitory returns, to FEEDBACK_BETA and BETA in each phase, use STDP3/LTP.
They regulate reset activity; their presence is not evidence of improved walking.

The sensor path uses four input neurons, four sensory high-gamma T10 neurons and
four CONTACT_MATCH_HG T10 neurons per foot. A parallel four-neuron RETURN_VETO_HG
T10 blocks unarmed contact; DONE inhibits that veto at strength 64. The captured
READY output and its HG helper have one neuron each. These sensory gates serve
a different role from the unchanged 24-neuron high-gamma T5 tilt reflexes.

In the local native-cell checks, holding rear-left contact at zero keeps A
selected. Supplying it during return requests B and recruits front-left movement.
An early pulse before return does not advance the switch. Standing contacts do
not start walking. See [CONTACT_SWITCH_CHECK.json](CONTACT_SWITCH_CHECK.json)
and [VALIDATION.md](VALIDATION.md) for all ten cases and their limits.

A bumper reports collision, not backward force or supported load. This circuit
accepts contact during return even if the foot never left the floor. Confirm
actual foot travel, support and body motion in Webots; the neural checks alone
cannot establish them. Existing motor calibration, foot physics, reflexes and
controller transport are unchanged.
