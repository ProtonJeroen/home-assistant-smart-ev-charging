"""Capacity calculation, rejection, pause, persistence and quality contracts."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('health', Path(__file__).parents[1] / 'custom_components/smart_ev_charging/battery_health.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CONTEXT = [28, 92, 'sensor.soc', 'binary_sensor.connected', 'sensor.energy']


class HealthTest(unittest.TestCase):
    def setUp(self):
        self.h = module.BatteryHealth()

    def session(self, capacity=26.6, start=20, end=100):
        self.h.observe(True, start, 0, CONTEXT)
        self.h.observe(True, end, capacity * (end-start) / 92, CONTEXT)
        return self.h.observe(False, None, None, CONTEXT)

    def test_three_sessions_and_capacity_formula(self):
        self.session()
        self.session()
        self.assertIsNone(self.h.capacity)
        self.session()
        self.assertAlmostEqual(self.h.capacity, 26.6)
        self.assertAlmostEqual(100*self.h.capacity/28, 95)
        self.assertEqual(self.h.quality, 'provisional_estimate')

    def test_partial_sessions_and_pauses(self):
        for _ in range(3):
            self.h.observe(True, 30, 5, CONTEXT)
            self.h.observe(True, 50, 11, CONTEXT)
            for _ in range(10):
                self.h.observe(True, 50, 11, CONTEXT)
            self.h.observe(True, 80, 20, CONTEXT)
            self.h.observe(False, None, 0, CONTEXT)
        self.assertAlmostEqual(self.h.capacity, 27.6)
        self.assertEqual(len(self.h.samples), 3)

    def test_reject_small_span_reset_drop_missing_and_implausible(self):
        self.session(start=80, end=100)
        self.assertEqual(self.h.reason, 'soc_span_too_small')
        for bad_soc, bad_energy, connected in [(None, 10, True), (50, None, True),
                (50, 10, None), (19, 10, True), (50, 0, True),
                (float('nan'), 10, True), (50, float('inf'), True)]:
            self.h.observe(True, 20, 5, CONTEXT)
            self.h.observe(connected, bad_soc, bad_energy, CONTEXT)
            self.h.observe(True, 100, 30, CONTEXT)
            self.h.observe(False, None, None, CONTEXT)
        self.session(capacity=100)
        self.assertEqual(self.h.samples, [])

    def test_persistence_and_no_active_session_restore(self):
        self.session()
        self.session()
        self.session()
        self.h.observe(True, 20, 0, CONTEXT)
        restored = module.BatteryHealth()
        restored.restore(self.h.export(), CONTEXT)
        self.assertEqual(restored.capacity, self.h.capacity)
        self.assertIsNone(restored.active)
        restored.observe(False, None, None, CONTEXT)
        self.assertEqual(len(restored.samples), 3)

    def test_context_change_resets_and_corrupt_storage_is_ignored(self):
        self.session()
        changed = list(CONTEXT)
        changed[1] = 90
        self.h.observe(True, 20, 0, changed)
        self.assertEqual(self.h.samples, [])
        for data in [None, [], {'context': CONTEXT, 'samples': 'bad'},
                     {'context': CONTEXT, 'samples': [None, 'bad', float('nan'), -1]}]:
            restored = module.BatteryHealth()
            restored.restore(data, CONTEXT)
            self.assertEqual(restored.samples, [])

    def test_quality_spread_retention_and_no_capping(self):
        for _ in range(5):
            self.session(capacity=28.5)
        self.assertEqual(self.h.quality, 'consistent_estimate')
        self.assertGreater(100*self.h.capacity/28, 100)
        self.session(capacity=16)
        self.assertEqual(self.h.quality, 'provisional_estimate')
        for _ in range(25):
            self.session()
        self.assertEqual(len(self.h.samples), 20)

    def test_duplicate_disconnect_does_not_count_twice(self):
        self.session()
        for _ in range(3):
            self.h.observe(False, None, None, CONTEXT)
        self.assertEqual(len(self.h.samples), 1)
