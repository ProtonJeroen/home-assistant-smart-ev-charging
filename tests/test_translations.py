"""Keep labels aligned with the actual options form and control reasons."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1] / 'custom_components/smart_ev_charging'


class TranslationTest(unittest.TestCase):
    def test_options_fields_and_control_states_have_en_nl_labels(self):
        constants = {}
        for node in ast.parse((ROOT / 'const.py').read_text(encoding='utf-8')).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
        flow = ast.parse((ROOT / 'config_flow.py').read_text(encoding='utf-8'))
        schema = next(n for n in flow.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'PROVIDER_OPTIONS_SCHEMA' for t in n.targets))
        fields = {constants[n.args[0].id] for n in ast.walk(schema)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr in ('Required', 'Optional') and n.args
                  and isinstance(n.args[0], ast.Name) and n.args[0].id in constants}
        fields.update(('charger_start_entity', 'charger_stop_entity', 'charger_limit_entity'))
        control = ast.parse((ROOT / 'charger_control.py').read_text(encoding='utf-8'))
        reasons = next(ast.literal_eval(n.value) for n in control.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'CONTROL_STATUSES' for t in n.targets))
        for language in ('en', 'nl'):
            data = json.loads((ROOT / 'translations' / f'{language}.json').read_text(encoding='utf-8'))
            step = data['options']['step']['providers']
            self.assertEqual(set(step['data']), fields)
            self.assertEqual(set(step['data_description']), fields)
            self.assertEqual(set(data['entity']['sensor']['charger_control_status']['state']), set(reasons))
            self.assertTrue(all(label and label != key for key, label in step['data'].items()))
        english = json.loads((ROOT / 'translations/en.json').read_text(encoding='utf-8'))
        source = json.loads((ROOT / 'strings.json').read_text(encoding='utf-8'))
        self.assertEqual(source, english)
