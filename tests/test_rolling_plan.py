"""Planner and actual runtime strategy tests without a Home Assistant install."""
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1] / 'custom_components/smart_ev_charging'
pkg = ModuleType('_smart_ev_test')
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
dt = SimpleNamespace(now=lambda: NOW, parse_datetime=datetime.fromisoformat,
                     get_time_zone=lambda _: timezone.utc, DEFAULT_TIME_ZONE=timezone.utc)
modules = {
    'homeassistant': ModuleType('homeassistant'),
    'homeassistant.const': SimpleNamespace(Platform=SimpleNamespace(SENSOR='sensor', BINARY_SENSOR='binary_sensor', NUMBER='number', SELECT='select', DATETIME='datetime'), STATE_UNAVAILABLE='unavailable', STATE_UNKNOWN='unknown'),
    'homeassistant.config_entries': SimpleNamespace(ConfigEntry=object),
    'homeassistant.core': SimpleNamespace(Event=object, HomeAssistant=object, callback=lambda f: f),
    'homeassistant.helpers': ModuleType('homeassistant.helpers'),
    'homeassistant.helpers.event': SimpleNamespace(async_track_state_change_event=lambda *a: None, async_track_time_interval=lambda *a: None),
    'homeassistant.util': SimpleNamespace(dt=dt),
}
with patch.dict(sys.modules, modules):
    runtime_module = importlib.import_module('_smart_ev_test.coordinator')
    planner = importlib.import_module('_smart_ev_test.planner')
    models = importlib.import_module('_smart_ev_test.models')
    const = importlib.import_module('_smart_ev_test.const')


def prices(count=24, minutes=60):
    return tuple(models.PriceSlot(NOW + timedelta(minutes=i*minutes), NOW + timedelta(minutes=(i+1)*minutes), float(i)) for i in range(count))


class RollingPlannerTest(unittest.TestCase):
    def test_selects_4_5_and_16_hours(self):
        for hours in (4, 5, 16):
            plan = planner.calculate_rolling_plan(prices(), NOW, hours, 24*60, 3.6)
            self.assertTrue(plan.coverage_complete)
            self.assertEqual(plan.planned_minutes, hours*60)
            self.assertEqual([s.price for s in plan.slots], list(range(hours)))

    def test_soc_need_shortens_hours(self):
        plan = planner.calculate_rolling_plan(prices(), NOW, 5, 75, 3.6)
        self.assertEqual(plan.planned_minutes, 75)
        self.assertEqual(plan.slots[-1].minutes, 15)

    def test_quarters_and_noncontiguous_negative_prices(self):
        slots = list(prices(96, 15))
        for i in (3, 8, 30, 70):
            s = slots[i]
            slots[i] = models.PriceSlot(s.start, s.end, -1)
        plan = planner.calculate_rolling_plan(tuple(slots), NOW, 1, 500, 3.6)
        self.assertEqual([s.start for s in plan.slots], [slots[i].start for i in (3,8,30,70)])
        self.assertLess(plan.estimated_cost, 0)

    def test_partial_current_interval_and_outside_horizon(self):
        slots = prices(26)
        now = NOW + timedelta(minutes=30)
        plan = planner.calculate_rolling_plan(slots, now, 1, 300, 3.6)
        self.assertEqual(plan.slots[0].start, now)
        self.assertEqual(plan.slots[0].minutes, 30)
        self.assertEqual(plan.planned_minutes, 60)
        self.assertTrue(all(now <= s.start < now+timedelta(hours=24) for s in plan.slots))

    def test_missing_prices_and_gap(self):
        for slots in (prices(23), prices()[:10]+prices()[11:], ()):
            self.assertFalse(planner.calculate_rolling_plan(slots, NOW, 4, 300, 3.6).coverage_complete)

    def test_dst_uses_24_elapsed_hours(self):
        # Simulate the autumn offset change using aware instants on either side.
        local_now = datetime(2026, 10, 25, 0, tzinfo=timezone(timedelta(hours=2)))
        start = local_now.astimezone(timezone.utc)
        slots = tuple(models.PriceSlot(start+timedelta(hours=i), start+timedelta(hours=i+1), 1) for i in range(24))
        plan = planner.calculate_rolling_plan(slots, local_now, 24, 1440, 3.6)
        self.assertEqual(plan.planned_minutes, 1440)
        self.assertEqual(plan.slots[-1].end-start, timedelta(hours=24))

    def test_invalid_hours(self):
        for hours in (0, 25, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                planner.calculate_rolling_plan(prices(), NOW, hours, 300, 3.6)


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.state = SimpleNamespace(state='40', attributes={})
        self.price = SimpleNamespace(state='0.10', attributes={'prices':[{'from':s.start, 'till':s.end, 'price':s.price} for s in prices()]})
        self.hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity: self.state if entity == 'sensor.soc' else self.price), config=SimpleNamespace(time_zone='UTC'))
        entry = SimpleNamespace(data={'soc_entity':'sensor.soc', 'battery_capacity_kwh':28}, options={'charging_mode':'smart_24h','price_entity':'sensor.prices','charge_power_kw':3.6,'cheap_hours':4})
        self.r = runtime_module.SmartEVChargingRuntime(self.hass, entry)

    def test_without_departure_starts_in_selected_slot(self):
        self.assertIsNone(self.r.departure)
        self.assertTrue(self.r.smart_plan_ready)
        self.assertTrue(self.r.preferred_charge_now)
        self.assertFalse(self.r.must_charge_now)
        self.assertEqual(self.r.requested_power_w, 3600)
        self.assertEqual(self.r.status, 'smart_charge_slot')
        self.assertIsNone(self.r.latest_start)

    def test_existing_deadline_never_forces_24h_mode(self):
        self.r._settings['departure'] = (NOW-timedelta(hours=1)).isoformat()
        self.price.attributes['prices'] = [{'from':s.start, 'till':s.end, 'price':100-s.price} for s in prices()]
        self.assertFalse(self.r.must_charge_now)
        self.assertFalse(self.r.preferred_charge_now)
        self.assertEqual(self.r.requested_power_w, 0)
        self.assertEqual(self.r.status, 'waiting_for_smart_slot')

    def test_missing_prices_waits_even_with_expired_deadline(self):
        self.r._settings['departure'] = (NOW-timedelta(hours=1)).isoformat()
        self.price.attributes['prices'] = self.price.attributes['prices'][:23]
        self.assertFalse(self.r.smart_plan_ready)
        self.assertEqual(self.r.requested_power_w, 0)
        self.assertEqual(self.r.status, 'waiting_for_price_data')

    def test_unavailable_price_source_does_not_use_old_attributes(self):
        self.price.state = 'unavailable'
        self.assertFalse(self.r.smart_plan_ready)
        self.assertEqual(self.r.requested_power_w, 0)
        self.assertEqual(self.r.status, 'waiting_for_price_data')

    def test_soc_loss_and_target(self):
        for value, status in [('unavailable', 'vehicle_data_unavailable'), ('80','target_reached')]:
            self.state.state = value
            self.assertEqual(self.r.requested_power_w, 0)
            self.assertEqual(self.r.status, status)

    def test_existing_smart_mode_still_needs_departure(self):
        self.r._settings['charging_mode'] = 'smart'
        self.assertFalse(self.r.preferred_charge_now)
        self.assertEqual(self.r.status, 'departure_not_set')

    def test_hours_cap_does_not_require_full_soc_duration(self):
        self.r._settings['cheap_hours'] = 0.25
        self.assertTrue(self.r.smart_plan_ready)
        self.assertEqual(self.r.planned_minutes, 15)
        self.assertGreater(self.r.charging_estimate.duration_minutes, 15)

if __name__ == '__main__':
    unittest.main()
