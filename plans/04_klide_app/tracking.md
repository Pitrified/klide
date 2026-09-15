# klide app tracking

The app itself, restarted from a simulator because the device is not here and a rendered frame is the evidence
an agent can check its own work against. Analysis and decisions in [`00_start.md`](00_start.md);
the requirements it inherits are in [`../00_initial/00_start.md`](../00_initial/00_start.md) and
[`../02_kobo/`](../02_kobo/). How the work is run is the meta track, [`../03_meta/tracking.md`](../03_meta/tracking.md).

## Key decisions

- The stack is chosen against a written requirement list, not by racing prototypes (AD1).
- The simulator is headless and emits frames; the viewer is a thin layer on top (AD2).
- It imitates what can make a frame wrong or a design bad, and stands in for the client as well as the panel (AD3, AD4).
- One wire protocol for the simulator and the real device (AD5).
- The frame is the evidence, which is where this track meets the meta one (MD10).

## Phases

| #  | Phase                      | Plan                                                          | Status  |
| -- | -------------------------- | ------------------------------------------------------------- | ------- |
| 1  | Requirements and stack     | [`01_requirements_and_stack.md`](01_requirements_and_stack.md) | planned |
| 2  | Walking skeleton           | [`02_walking_skeleton.md`](02_walking_skeleton.md)             | planned |
| 3  | Simulator fidelity         | [`03_simulator_fidelity.md`](03_simulator_fidelity.md)         | planned |
| 4  | Host renderer and views    | [`04_host_renderer.md`](04_host_renderer.md)                   | planned |
| 5  | Device client              | [`05_device_client.md`](05_device_client.md)                   | draft   |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-09-16 : folded in A1-A7 and derived the five phases. The stack is decided against written requirements rather than by a race, the simulator is headless and covers the client as well as the panel, ghosting is deferred, GPU waits for a measurement, and the evidence format is left to the first real frame comparison in phase 2
