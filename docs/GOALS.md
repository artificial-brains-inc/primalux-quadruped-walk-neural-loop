# Build the walking goal and decide its interactions

Start with the behavioral requirement: a START request should enable coordinated
stepping, and a STOP request should suppress it. The adapter publishes one input event. A neural request latch retains the request
until the new goal takes over and clears it. Separate request capture, the retained
goal, phase interaction and local actuator expression.

| Relationship | Purpose |
| --- | --- |
| START request latch recruits WALK and clears REST | Enable a persistent goal through an internal reinforcing loop |
| STOP request latch recruits REST and clears WALK | Oppose the goal and its recurrence, including held outputs |
| WALK_DRIVE excites A and B equally | Supply both candidate phases without permanently favoring one |
| Startup bias inhibits B until A's inhibitor recruits | Give A an initial opportunity without host timing |
| Intermediate A prepares B, and B prepares A | Make the next action available through internal feedback |
| A's inhibitor suppresses B | Hold the competing phase back |
| A's downstream release inhibits A's inhibitor | Release B through double inhibition |
| B performs the same operation in reverse | Provide a symmetric return path |
| The taking-over inhibitor clears the opposite release state | Allow the next cycle to recruit inhibition again |
| Each phase recruits local motor Betas in four leg groups | Coordinate diagonal pairs while retaining separate actuators |
| Opposing movements at one joint inhibit each other | Put competition at the physical antagonist relationship |
| Tilt toward a leg recruits its fast support reflex | Add physical evidence to the motor goal |
| The reflex inhibits local flexion and excites knee extension | Give support priority at the physical antagonist |
| Its downstream reset inhibits its own trigger and clears both readouts | End the burst and permit later evidence to recruit it again |
| Each reflex leaves other legs and gait phases untouched | Allow several local support goals to coexist |
| REST clears phase, local motor and reflex states | Make STOP apply throughout the recurrent network |

When adding a goal, identify what recruits it, what maintains it, what inhibits it,
and what clears its output. Then decide which other goals should cooperate,
compete or become available when it releases inhibition. Strength belongs on the
inhibitory connection; rhythm and TNorm describe the receiving relationship.

Useful internal activity connects directly to the next population. It does not
need to become a new input calculated and republished by the controller. The three
command neurons remain START, STOP and ACK. A fourth neuron carries outcome reward.
Four more neurons encode signed physical roll/pitch. Their combination is resolved
inside the neural graph, never translated into leg commands by Python.

## Decide what should learn

Keep the meaning of START, STOP and ACK fixed. Choose plastic connections where
competition and release can affect coordination. Define reward from an independent
physical outcome: new forward progress while upright. Do not reward a phase simply
for firing; that could reinforce activity without achieving the walking goal.

The goal circuit chooses and maintains activity. Local inhibitory eligibility
and the common reward modulate the 66 selected connections. The reward adapter
measures outcome only; it never says which leg should move or when A/B should switch.
One common reward is a minimal teaching design, with coarse credit assignment.

Internal recurrence cannot sense contact or slipping. GPS and orientation provide
physical evidence for reward, and roll/pitch now supply local support reflexes.
There is still no foot-contact sensor: an extension can only support the body if
the foot can reach suitable ground. Read [the reflex goal and its interactions](REFLEX.md).
The reward can accept upright sliding, so inspect footage and joint/body traces
before calling the result walking. The servos hold neutral targets when local
motor outputs clear.
