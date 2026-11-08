# Requirements and troubleshooting

Use an existing **Webots R2025a** installation. The project includes its own copy
of Spot's model dependencies in `protos/`, linked through relative paths.
The floor, walls, background and light use built-in Webots nodes.
This package does not install Webots or modify its sample controllers or robot
files. Webots is available separately from
https://github.com/cyberbotics/webots/releases/tag/R2025a.

| Symptom | Check |
| --- | --- |
| Missing pip in `.venv` | Run `bash install.sh`; the installer repairs pip or preserves/replaces an incomplete environment |
| Reward type rejected during Build | Use SDK 0.4.2 locally and Device Manager 0.6.17 with compatible builder 0.4.11 on Prima-Lux; install.sh updates only the local SDK |
| Missing device API key | Put the Prima-Lux developer API key in `.env` |
| Invalid Webots executable | Point WEBOTS_EXECUTABLE at the executable file, not a folder |
| Missing bundled Webots asset | Restore the complete project including `protos/` and `assets/`; Run checks these before contacting the device |
| `webots://` fallback / skipped Spot PROTO | Open this project's `worlds/spot_neural_walk.wbt`; its Spot declaration must be `../protos/spot/Spot.proto` |
| Installed brain mismatch | Build this folder's saved design and wait for READY |
| W is received and ACKed, but REST stays active | Build the request-latch graph from this package; updating Python alone does not replace the installed brain. Inspect start_request/stop_request alongside WALK/REST |
| No W/S key event appears | Click the Webots 3D view; check commands.jsonl |
| Neural activity but no motion | Rhythm mode intentionally holds standing targets; inspect local motor outputs in normal mode |
| Motion but no useful gait | Compare phase ordering, joint directions, clearances and body tilt; the first composition is not a validated gait |
| Stop/save unconfirmed | Keep the terminal open and inspect `ab device --env .env status` |

The requirements file pins artificialbrains_sdk==0.4.2, installed from PyPI. Changing the SDK,
body model, joint limits or input contract requires rechecking the integration.
