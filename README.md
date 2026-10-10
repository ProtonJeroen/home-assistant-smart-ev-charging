# Smart EV Charging for Home Assistant

Smart EV Charging is a custom Home Assistant integration for planning EV charging around dynamic energy prices, departure deadlines, charger limits and learned battery behaviour.

## Project goals

The integration is designed around interchangeable providers:

- **Vehicle data** — initially a generic Home Assistant SOC entity, later WiCAN Pro and other vehicle sources.
- **Energy prices** — initially Home Assistant entities such as Frank Energie, later additional price providers.
- **Charger control** — planned for a later release, with Easee as the first charger adapter.
- **Home Energy Manager** — Smart EV Charging exposes a generic requested-power signal so a central energy manager can decide how much power the EV may use.
- **Battery learning** — future versions will learn usable battery capacity, charging efficiency and an estimated capacity-based SOH from real charging sessions.

## Current scope — v0.2

Version 0.2 is deliberately safe and does **not** control the charger.

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
- a strategy status sensor;
- requested charging power in watts for future Home Energy Manager integration.

### Smart mode in v0.2

The quarter-hour price planner is not connected yet. Smart mode therefore waits for future price data and only requests charging once the latest safe start time has been reached.

This keeps v0.2 safe to test alongside existing automations.

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

Smart EV Charging currently produces calculation and request signals only. It does not start, stop or change the current limit of a real charger yet.

## Status

Early development / experimental.
