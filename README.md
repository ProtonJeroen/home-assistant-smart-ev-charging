# Smart EV Charging for Home Assistant

Smart EV Charging is a custom Home Assistant integration for planning EV charging around dynamic energy prices, departure deadlines, charger limits and learned battery behaviour.

## Project goals

The integration is designed around interchangeable providers:

- **Vehicle data** — initially a generic Home Assistant SOC entity, later WiCAN Pro and other vehicle sources.
- **Energy prices** — a generic Home Assistant price entity; Frank Energie is the first tested provider.
- **Charger control** — planned for a later release, with Easee as the first charger adapter.
- **Home Energy Manager** — Smart EV Charging exposes a generic requested-power signal so a central energy manager can decide how much power the EV may use.
- **Battery learning** — future versions will learn usable battery capacity, charging efficiency and an estimated capacity-based SOH from real charging sessions.

## Current scope — v0.3

Version 0.3 is deliberately safe and does **not** control the charger.

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
- next planned charge start;
- estimated charging cost;
- energy-weighted average charging price;
- planned slots exposed as attributes on the estimated-cost sensor.

## Frank Energie

The maintained Frank Energie integration exposes its full price horizon in a `prices` attribute with entries containing `from`, `till` and `price`.

For Smart EV Charging, configure the **current all-in electricity price** sensor as the electricity price source.

After installing v0.3:

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

Smart EV Charging currently produces calculation, planning and power-request signals only. It does not start, stop or change the current limit of a real charger yet.

## Status

Early development / experimental.
