"""Control contract tests, including the Easee script service adapter."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('control', Path(__file__).parents[1] / 'custom_components/smart_ev_charging/charger_control.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ControlTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = []
        self.options = dict(charger_control_enabled=True, charger_start_entity='script.easee_resume', charger_stop_entity='script.easee_pause', charger_limit_entity='script.easee_current', charger_phases=1)
        self.r = SimpleNamespace(entry=SimpleNamespace(options=self.options), current_soc=40, target_soc=80, charger_connected=True, preferred_charge_now=True, must_charge_now=False, requested_power_w=3600)
        self.r.hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: SimpleNamespace(state='off')), services=SimpleNamespace(has_service=lambda *_: True, async_call=self.call), async_create_task=asyncio.create_task)
        self.c = module.ChargerControl(self.r)

    async def call(self, domain, service, data, blocking):
        self.calls.append((domain, service, data))

    async def run_control(self):
        self.c.schedule()
        await self.c.task

    async def test_limit_before_resume_and_deduplicate(self):
        await self.run_control()
        await self.run_control()
        self.assertEqual(self.calls, [('script', 'easee_current', {'current': 15}), ('script', 'easee_resume', {})])

    async def test_invalid_inputs_never_take_over_manual_session(self):
        for field, value in [('current_soc', None), ('current_soc', float('nan')), ('current_soc', 80), ('charger_connected', None), ('charger_connected', False), ('requested_power_w', float('inf')), ('requested_power_w', 1200)]:
            old = getattr(self.r, field)
            setattr(self.r, field, value)
            await self.run_control()
            setattr(self.r, field, old)
        self.assertEqual(self.calls, [])

    async def test_owned_session_stops_on_soc_loss_and_target(self):
        for soc in (None, 80):
            self.r.current_soc = 40
            await self.run_control()
            self.r.current_soc = soc
            await self.run_control()
            self.assertEqual(self.calls[-1][1], 'easee_pause')

    async def test_disabled_no_commands(self):
        self.options['charger_control_enabled'] = False
        await self.run_control()
        self.assertEqual(self.calls, [])

    async def test_waiting_stops_and_deadline_can_start(self):
        await self.run_control()
        self.r.preferred_charge_now = False
        self.r.requested_power_w = 0
        await self.run_control()
        self.assertEqual(self.calls[-1][1], 'easee_pause')
        self.r.must_charge_now = True
        self.r.requested_power_w = 3600
        await self.run_control()
        self.assertEqual(self.calls[-1][1], 'easee_resume')

    async def test_change_during_limit_blocks_start(self):
        async def changed(*args, **kwargs):
            await self.call(*args, **kwargs)
            self.r.current_soc = None
        self.r.hass.services.async_call = changed
        await self.run_control()
        self.assertEqual(len(self.calls), 1)

    async def test_limit_failure_never_starts(self):
        async def failed(*args, **kwargs):
            raise RuntimeError('offline')
        self.r.hass.services.async_call = failed
        with self.assertLogs('control', level='ERROR'):
            await self.run_control()
        self.assertFalse(self.c.owned)

    async def test_missing_service(self):
        self.r.hass.services.has_service = lambda *_: False
        await self.run_control()
        self.assertEqual(self.calls, [])

    async def test_unload(self):
        self.c.cancel()
        self.c.schedule()
        self.assertIsNone(self.c.task)

    async def test_selected_invalid_telemetry_stops_owned_session(self):
        await self.run_control()
        self.options['charger_power_entity'] = 'sensor.easee_power'
        self.r.hass.states.get = lambda _: SimpleNamespace(state='unavailable')
        await self.run_control()
        self.assertEqual(self.calls[-1][1], 'easee_pause')

    async def test_failed_start_attempts_stop(self):
        async def failed(domain, service, data, blocking):
            await self.call(domain, service, data, blocking)
            if service == 'easee_resume':
                raise RuntimeError('uncertain acknowledgement')
        self.r.hass.services.async_call = failed
        with self.assertLogs('control', level='ERROR'):
            await self.run_control()
        self.assertEqual(self.calls[-1][1], 'easee_pause')
        self.assertFalse(self.c.owned)

    async def test_disabled_owned_session_has_no_commands(self):
        await self.run_control()
        count = len(self.calls)
        self.options['charger_control_enabled'] = False
        self.r.current_soc = None
        await self.run_control()
        self.assertEqual(len(self.calls), count)

    async def test_current_update_and_three_phases(self):
        await self.run_control()
        self.options['charger_phases'] = 3
        self.r.requested_power_w = 11000
        await self.run_control()
        self.assertEqual(self.calls[-3:], [('script', 'easee_pause', {}), ('script', 'easee_current', {'current': 15}), ('script', 'easee_resume', {})])

    def test_current_boundaries(self):
        for phases in (1, 3):
            self.assertIsNone(module.requested_current(230 * phases * 6 - 1, phases))
            self.assertEqual(module.requested_current(230 * phases * 6, phases), 6)
            self.assertEqual(module.requested_current(50000, phases), 16)

if __name__ == '__main__':
    unittest.main()
