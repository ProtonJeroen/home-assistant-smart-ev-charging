# Smart EV Charging for Home Assistant

Smart EV Charging is a custom Home Assistant integration for planning EV charging around dynamic energy prices, departure deadlines, charger limits and learned battery behaviour.

## Project goals

The integration is designed around interchangeable providers:

- **Vehicle data** — initially a generic Home Assistant SOC entity, later WiCAN Pro and other vehicle sources.
- **Energy prices** — initially Home Assistant entities such as Frank Energie, later additional price providers.
- **Charger control** — planned for a later release, with Easee as the first charger adapter.
- **Home Energy Manager** — Smart EV Charging will expose a generic power request so a central energy manager can decide how much power the EV may use.
- **Battery learning** — future versions will learn usable battery capacity, charging efficiency and an estimated capacity-based SOH from real charging sessions.

## Version 0.1 scope

Version 0.1 is deliberately safe and does **not** control the charger.

It will focus on:

- selecting a vehicle SOC entity;
- configuring an initial usable battery capacity;
- calculating required battery energy;
- calculating required grid energy;
- estimating charging duration;
- preparing the foundation for target SOC, departure planning and quarter-hour price optimisation.

The first calculation layer is already separated into `models.py` and `planner.py`, so later vehicle, charger and price adapters do not need to contain charging logic.

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

## Repository layout

```text
custom_components/
└── smart_ev_charging/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── config_flow.py
    ├── models.py
    ├── planner.py
    └── translations/
        ├── en.json
        └── nl.json
```

Additional platforms and provider adapters will be added incrementally.

## Status

Early development / experimental. Do not use this project yet to control a real charger.
