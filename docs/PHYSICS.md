# Distinguishing extension from support problems

The uploaded run reached its rear-right return angle (approximately −0.08 rad)
while rear-right touch stayed zero. Front-left hip position was approximately
+0.307 rad against a −0.16 rad target. Those are different failure symptoms:
the first joint reached its command without obtaining contact; the second did
not track its command. They do not by themselves establish a center-of-mass cause.

This package keeps the current joint targets and speeds so the sensor-terminated
loop can be compared independently. It adds these read-only fields to each
observations.jsonl row:

| Field | Meaning |
| --- | --- |
| center_of_mass_xyz_m | World position of the robot's center of mass, including descendant solids |
| foot_center_xyz_m | World positions of the four bumper node origins; these are foot centers, not contact points |
| joint_motor_torque_nm | Motor torque feedback for each joint |
| physical_measurement_errors | Unavailable or non-finite diagnostic readings; missing evidence is never replaced by zero |

Compare center-of-mass projection with the measured supporting feet. Compare
actual joint position and target together with motor torque. A persistent large
position discrepancy near the model's available torque suggests a load or
constraint problem to investigate; it does not prove the cause. Torque feedback
covers motor effort, not every external or constraint force. The bundled motor
maximum is 50 Nm. Do not increase it or retune all joint angles without checking
the observations.

The Supervisor readings and torque feedback never enter the brain or change
actuator commands. Four measured foot sensors and the existing tilt/reward
inputs remain the only physical evidence used for behavior.

Webots API references:
- https://cyberbotics.com/doc/reference/supervisor
- https://cyberbotics.com/doc/reference/motor
