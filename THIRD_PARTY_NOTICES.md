# Third-party references and assets

## Webots and Spot

This repository includes the Cyberbotics Webots R2025a Spot model under
`protos/spot/`: its two PROTOs, meshes and textures. The Spot PROTO identifies
Creative Commons Attribution 4.0 and credits the original model to Greg McKechnie.
The included license is [CC-BY-4.0](licenses/CC-BY-4.0.txt).
Spot and Boston Dynamics are names of their respective owners;
this example is not affiliated with or endorsed by Boston Dynamics.

The five material PROTOs and their textures under `protos/appearances/` come from
the same Webots release. The appearance PROTOs identify Apache License 2.0;
the Webots repository's [Apache-2.0 license](licenses/Apache-2.0.txt) is included.
Their original file notices are retained.

Only Spot.proto and SpotLeg.proto were modified: their appearance declarations
use relative paths to the bundled copies. Spot.proto also removes its five Camera
devices; their visible housings remain. SpotLeg.proto moves the existing distal
foot-pad collision cylinder into a child bumper TouchSensor; it removes the
parent copy so another collider cannot mask the sensor. Each modified file marks
those changes. The cylinder shape and pose, joints, limits, masses, inertias and
actuator parameters are preserved; the bumper adds no separate Physics body. Meshes, textures and the appearance PROTOs are unmodified.
`assets/webots-assets.json` lists every bundled upstream URL and file digest.
These third-party assets and the relative-path adaptations retain their upstream
licenses; the Artificial Brains product restriction does not apply to them.

Model source:
https://github.com/cyberbotics/webots/blob/R2025a/projects/robots/boston_dynamics/spot/protos/Spot.proto

The neutral posture and primary actuator names are based on Cyberbotics' official
sample controller, copyright 1996–2024 Cyberbotics Ltd., Apache License 2.0:
https://github.com/cyberbotics/webots/blob/R2025a/projects/robots/boston_dynamics/spot/controllers/spot_moving_demo/spot_moving_demo.c
https://www.apache.org/licenses/LICENSE-2.0

No sample gait or timed motion routine is incorporated into the runtime.

## Research reference

Pugliese et al., *Connectome simulations identify a central pattern generator
circuit for fly walking*. https://doi.org/10.1101/2025.09.12.675944
The paper is cited, not redistributed. Its model is not included or reimplemented.

## SDK

The Artificial Brains SDK is installed as a separate dependency under its own
terms. No private builder, neural construction implementation, firmware, device
credential or compiled brain image is included.
