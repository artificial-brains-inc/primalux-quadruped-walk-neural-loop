# Four physical feet, explicit evidence, neural memory

The four bundled foot-pad TouchSensors are bumpers: 0 means no collision and 1
means collision. Each has a positive-mass 10 g Physics body, its original pose
and shape, and no duplicate parent pad collider. The four pads add 40 g. A
collision reading does not measure force or prove the foot supports body weight.

Each current reading is encoded in two four-neuron populations:

| Measurement | CONTACT rail | AIR rail |
| --- | --- | --- |
| Collision | four ones | four zeros |
| No collision | four zeros | four ones |
| Suspended during recovery / shutdown | four zeros | four zeros |

This is eight named populations for four sensors, not eight physical sensors.
The separate AIR rail matters because asynchronous input silence is not a
measurement of lift-off. Python only computes the complement of the same
binary sample. It keeps no leg phase, contact-edge history or handoff timer.

For one leg, its ACTIVE_HG inhibits AIR_ACTIVE_VETO_HG. Fresh AIR evidence can
then pass AIR_MATCH_HG and set retained AIR_SEEN. Other legs' AIR cannot arm
this leg. At landing, CONTACT excites CONTACT_MATCH_HG, while two parallel
contact-driven vetoes suppress it unless AIR_SEEN_HG and DONE_HG respectively
inhibit those vetoes. MATCH sets retained CONTACT_READY. READY drives the local
handoff Beta, which requests the next leg through its inhibitory timing path.
Meanwhile RETURN_BETA has already recruited the next PREPARE_HG. Contact does
not gate that grounded preparation; it still gates capture of the next ACTIVE
turn. Preparation never clears the current turn or its contact memories.

REQUEST and STANCE clear stale AIR_SEEN. CONTACT_READY persists through STANCE
to keep the completed leg loop inhibited; only its next REQUEST or global
STOP/REST clears it. The raw sensory vetoes remain operational during REST. A foot already on
the floor at START cannot authorize a handoff without observed lift-off.

Fresh measurement captures are sent atomically with tilt and reward. Slow HTTP
replaces older unsent captures with the newest; it never blocks motor frames.
A sufficiently brief airborne interval could therefore be missed. In that case
the graph holds the turn and retries the local primitive; it does not fabricate
contact history or advance on a timer. Inspect raw `foot_contact`, encoded `contact_inputs`, accepted
`contact-inputs.jsonl` and neural AIR_SEEN/CONTACT_READY to locate the gap.

Sensor qualification relays and vetoes are static. The qualified contact helper
also inhibits its own LEG_LOOP_HG through STDP3/LTP feedback, terminating the
retained local attempt. The four BRAKE_BETA → HANDOFF_BETA paths also learn.
