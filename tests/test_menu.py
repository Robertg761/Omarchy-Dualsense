import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'dualsense'))
import config
spec = importlib.util.spec_from_file_location('dualsense_menu', Path(__file__).parents[1] / 'dualsense/menu.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)

class MenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path_patch = patch.object(config, 'CONFIG', Path(self.temp.name) / 'shortcuts.json')
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

    def test_records_show_current_shortcut_and_edit_action(self):
        values = config.DEFAULTS.copy()
        values['layer_cross'] = 'CTRL+T'
        config.save(values)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            menu.records()
        self.assertIn('Controller L2 + cross', output.getvalue())
        self.assertIn('CTRL+T  [edit]\texec\t', output.getvalue())
        self.assertIn('--edit layer_cross', output.getvalue())

    @patch.object(menu, 'select', return_value='Change shortcut')
    @patch.object(menu.subprocess, 'run')
    def test_edit_saves_new_chord(self, run, _select):
        run.side_effect = [SimpleNamespace(returncode=0, stdout='ctrl+alt+t\n'), SimpleNamespace(returncode=0)]
        menu.edit('layer_cross')
        self.assertEqual(config.load()['layer_cross'], 'CTRL+ALT+T')

    @patch.object(menu, 'select', return_value='Disable shortcut')
    @patch.object(menu.subprocess, 'run')
    def test_disable_saves_empty_action(self, _run, _select):
        menu.edit('layer_cross')
        self.assertEqual(config.load()['layer_cross'], '')

    @patch.object(menu, 'select', return_value='Change shortcut')
    @patch.object(menu.subprocess, 'run')
    def test_invalid_shortcut_is_not_saved(self, run, _select):
        run.side_effect = [SimpleNamespace(returncode=0, stdout='SUPER+NOT_A_KEY\n'), SimpleNamespace(returncode=0)]
        menu.edit('layer_cross')
        self.assertFalse(config.CONFIG.exists())

if __name__ == '__main__': unittest.main()
