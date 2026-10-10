# Smart EV Charging for Home Assistant

Smart EV Charging is a custom Home Assistant integration for planning EV charging around dynamic energy prices, departure deadlines, charger limits and learned battery behaviour.

## Project goals

The integration is designed around interchangeable providers:

- **Vehicle data** — initially a generic Home Assistant SOC entity, later WiCAN Pro and other vehicle sources.
- **Energy prices** — a generic Home Assistant price entity; Frank Energie is the first tested provider.
- **Charger control** — optional guarded control through selected Home Assistant scripts, with Easee as the first example.
- **Home Energy Manager** — Smart EV Charging exposes a generic requested-power signal so a central energy manager can decide how much power the EV may use.
- **Battery learning** — future versions will learn usable battery capacity, charging efficiency and an estimated capacity-based SOH from real charging sessions.

## Current scope — v0.5.0

Version 0.5 adds opt-in charger control, disabled by default.

It supports:

- selecting a vehicle SOC entity;
- configuring an initial usable battery capacity;
- target SOC;
- expected AC charging power;
- charging efficiency;
- departure date/time;
- a configurable safety margin before departure;
- calculated battery energy, grid energy and charge duration;
- latest safe start time;
- charging modes: Off, Charge now, Smart charge and Ready by departure;
- `preferred_charge_now` and `must_charge_now` signals;
- requested charging power in watts for future Home Energy Manager integration;
- a generic dynamic-price source using a Home Assistant sensor with a `prices` attribute;
- cheapest-slot planning across quarter-hour or hourly price intervals;
- current smart-charge block start and end while a selected block is active;
- next **future** planned charge start (the active block is no longer shown as the next start);
- charging-plan sensor whose state is the number of selected blocks and whose attributes contain all planned start/stop times, prices, minutes, energy and cost;
- total planned charging minutes;
- estimated charging cost;
- energy-weighted average charging price;
- planned slots exposed as attributes on the estimated-cost sensor;
- chart-ready electricity-price data with selected charge blocks marked separately;
- optional read-only charger data (status, connected state, actual power, current and session energy).

## Frank Energie

The maintained Frank Energie integration exposes its full price horizon in a `prices` attribute with entries containing `from`, `till` and `price`.

For Smart EV Charging, configure the **current all-in electricity price** sensor as the electricity price source.

After installing v0.4.0:

1. Open **Settings → Devices & services → Smart EV Charging**.
2. Open the integration menu and choose **Configure**.
3. Select the Frank Energie current all-in electricity-price sensor.
4. Set the charging mode to **Smart charge** and configure a departure time.

The planner only uses a smart schedule when price data continuously covers the planning window up to the requested ready time. If future prices are not published yet, the status remains **Waiting for price data**. The existing deadline fallback still takes priority, so once the latest safe start time is reached, charging becomes mandatory regardless of price availability.

## Smart plan behaviour

The planner:

1. calculates the remaining grid energy and required charge duration;
2. limits the planning window to now through departure minus the safety margin;
3. ranks all available price intervals by price;
4. selects enough of the cheapest intervals to meet the required duration;
5. allows non-contiguous charging periods;
6. may use only part of the final price interval when the remaining required duration is shorter than the whole slot.

For example, if 223 minutes of charging are required, the planner can select fourteen complete 15-minute intervals plus 13 minutes of one additional interval.

## Planned architecture

```text
Home Assistant
      |
      +-- Home Energy Manager
      |       |
      |       +-- Grid / PV / home battery / price decisions
      |       |
      |       +---- power permission ----+
      |                                  |
      +---------------------------+      |
                                  v      v
                         Smart EV Charging
                          |      |       |
                          |      |       +-- Price provider
                          |      |
                          |      +---------- Charger provider
                          |
                          +----------------- Vehicle provider
```

Smart EV Charging decides **what the vehicle needs and when**.  
The Home Energy Manager decides **how much power is available**.

## Safety

Charger control is disabled by default. Read the guarded control section before enabling it.

## Status

Early development / experimental.


## Plan visibility

Version 0.3.1 adds dedicated planning entities so a dashboard can show the schedule without reading raw attributes manually.

- **Current charge block start** — available only while a selected smart-price block is active.
- **Current charge block end** — when the current selected block will stop.
- **Next future charge start** — strictly the next selected block after the current moment; it no longer points at a block that is already active.
- **Charging plan** — the state is the number of selected blocks. Its attributes contain the full ordered slot list.
- **Planned charge duration** — total selected minutes.

The charging-plan attributes also contain the selected price source, coverage status, required/planned minutes, current block start/end and next future start.


## Price and charging bar chart

Version 0.4 adds a **Price and charge chart** sensor. Its `bars` attribute contains the known price horizon split into chart segments with:

- `from`
- `till`
- `midpoint`
- `price`
- `charging`

Planned smart-charge segments are marked with `charging: true`. This makes it possible to render the normal electricity price in yellow bars and the selected charging blocks in green bars.

An example for the HACS **ApexCharts Card** is included at:

`docs/apexcharts-price-plan-card.yaml`

Copy the YAML into a manual dashboard card and replace:

`sensor.REPLACE_ME_price_chart`

with the entity ID of the **Price and charge chart** sensor created for your vehicle.

## Easee read-only connection

Smart EV Charging intentionally reads charger data through existing Home Assistant entities instead of depending directly on one charger integration. This keeps the charger interface generic and lets Easee be the first provider without hard-coding Easee into the planner.

Open:

**Settings → Devices & services → Smart EV Charging → Configure**

You can optionally select:

- **Charger status entity** — for the Easee status sensor;
- **Vehicle connected entity** — when a suitable binary sensor is available;
- **Charger power entity** — actual Easee charging power;
- **Charger current entity** — actual charging current;
- **Session energy entity** — energy delivered in the current Easee session.

The integration normalizes:

- power to W;
- current to A;
- session energy to kWh.

These telemetry entities remain read-only; optional control is configured separately below.

For the current Easee dashboard shown during development, the most useful first mappings are the entities behind **Status**, **Vermogen** and **Sessie energie**. Current and connected-state sources are optional and can be added when suitable entities are available.

## Guarded charger control (0.5.0)

In **Configure**, select three distinct existing `script` entities: start/resume,
stop/pause, and current limit. The current script must accept `current` in amperes.
Also select a **Vehicle connected** binary sensor and the actual number of active
charging phases (1 or 3). Then explicitly enable **Charger control enabled**.
No charger brand is imported or discovered by the integration.

Layer 1 uses `preferred_charge_now OR must_charge_now` and positive
`requested_power` from the existing decision layer. Layer 2 sets the limit before
starting: `floor(requested_power / (230 V * phases))`, capped at 16 A. A request
below 6 A pauses an owned session rather than rounding up and exceeding power.
The phase setting must match actual charging; automatic phase switching is not
supported. This is nominal-voltage scheduling, not household load balancing.
Existing charger/circuit protections remain responsible for electrical safety.

Missing, non-finite, out-of-range SOC/target, disconnected/unknown vehicle state,
missing control scripts/services, or invalid selected charger telemetry block
start/current commands. Target reached, no charging demand or invalid inputs
pause a session previously started by this runtime. A manually started session
is never stopped when this runtime has not taken ownership. A start failure
triggers a best-effort stop because the command may have reached the charger.
Failures are logged and retried on a later source update or minute tick.
Commands run serially and unchanged requests are deduplicated. Inputs are checked
again after setting current before starting.

**Disabling control is an absolute no-command gate**, including stop commands.
Pause first if needed, then disable. Unloading/restarting Home Assistant cancels
pending work and forgets session ownership; it cannot guarantee a physical stop
when Home Assistant, the network, or Easee Cloud is unavailable. Changing tracked
telemetry selections reloads the integration and also resets ownership.
Configure charger-side safeguards separately. Do not run competing charging
automations or Easee schedules alongside this controller. Selected scripts must
be short, synchronous service wrappers without delays, queues or
`continue_on_error`. Service completion acknowledges a request, not physical
charging; check actual charger telemetry during commissioning.

### Easee setup

The maintained [Easee integration services](https://github.com/nordicopen/easee_hass/blob/master/custom_components/easee/services.yaml)
provide `easee.action_command` (`resume` / `pause`) and
`easee.set_charger_dynamic_limit` (`current`, optional `time_to_live`).
The current upstream integration has no native number platform for this limit.
Home Assistant [script actions](https://www.home-assistant.io/integrations/script/)
let us select existing services without hard-coding charger-specific fields.

Copy `docs/easee-control-scripts.yaml` into `scripts.yaml`, replace the device ID,
reload scripts, and select these three script entities in Configure. Use a real
connected binary sensor, or a template derived from your verified Easee status
values that becomes unavailable when its source is unavailable. Do not treat
unknown status as connected. Keep control disabled until mappings are verified.

Tests use an Easee-named script adapter with mocked Home Assistant services;
no real Easee charger or live Home Assistant instance was available for hardware
validation. Run `python -m unittest discover -s tests -v` for control contracts.
For commissioning, observe a low-current start, waiting-slot pause, deadline
start, SOC loss, disconnected vehicle and target reached, then disable control.
