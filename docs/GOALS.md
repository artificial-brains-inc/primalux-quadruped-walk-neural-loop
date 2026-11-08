# Building goals and choosing their interactions

A goal needs evidence that activates it, a way to retain activity when needed,
an output path that expresses it, and explicit conditions that end or oppose it.
A useful diagram should explain all four.

## WALK and REST

WALK_START recruits a retained request. That request activates WALK and opposes
REST. WALK reinforces itself and clears the completed request. STOP uses the
same pattern in the opposite direction. REST clears both switch states and all
motor outputs. A transport ACK confirms input-path activity, not the goal result.

## Two complementary actions

The switch selects a whole motor pattern. A supports one diagonal pair while
the other flexes and advances. B exchanges the roles. Opposing states inhibit
each other; unrelated joints can act together within the selected state.

Choose the relationships before choosing TNorms:

1. Which motor populations belong to A? Which belong to B?
2. Which opposing populations and bistable outputs must each state clear?
3. What internal evidence should request the handoff?
4. How does a request persist until the next state takes over?

Here, the selected hip output neurons provide internal evidence for a handoff
pathway. They indicate motor command activity, not contact or joint completion.
The resulting RELEASE requests the opposite state. Rear motor commands follow
the diagonal front partner through a relay, so front commands initiate first.
No controller-side timer or phase input is needed.

## A reflex is local priority

Tilt evidence supports extension and contradicts flexion in the affected leg.
The high-gamma T5 reflex directly drives its fast output, releases the regular
extension veto and resets through output feedback. The same high-gamma directly
excites the regular extension Beta through an STDP3 connection. It does not ask
the gait switch for permission or suppress another leg. Local priority is an
inhibitory relationship, not Python choosing between two motor commands.

## Decide what can adapt

Static neural dynamics establish retention, switching, competition and reflexes.
The four optional STDP3/LTP inhibitory returns adjust the release pathway's
recovery. Four excitatory STDP3/LTP edges connect reflex high-gamma directly to
the regular extension Betas. Their pre/post firing can create eligibility on
those connections; later dopamine can act on it. The fixed fast branch remains
available. Learning adjusts recruitment; it does not replace the source of
firing or guarantee earlier corrective action. Reward comes from physical
progress. First observe a working static behavior; then test whether learning improves it. Do not label accepted reward
events as dopamine spikes or proof of useful weight changes.
