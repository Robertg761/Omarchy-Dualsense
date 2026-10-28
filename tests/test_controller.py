import importlib.util
from pathlib import Path
import unittest
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "dualsense"))
from types import SimpleNamespace
from unittest.mock import patch
from evdev import AbsInfo, ecodes as e

spec = importlib.util.spec_from_file_location('controller', Path(__file__).parents[1] / 'dualsense/controller.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)

class Output:
    def __init__(self): self.events = []
    def write(self, *event): self.events.append(event)
    def syn(self): pass

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.output = Output()
        info = AbsInfo(128, 0, 255, 0, 0, 0)
        self.desktop = controller.Desktop(self.output, {code: info for code in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY, e.ABS_Z)})
    def event(self, typ, code, value, now=0):
        self.desktop.event(SimpleNamespace(type=typ, code=code, value=value), now)
    def test_click_released_on_layer_change(self):
        self.event(e.EV_KEY, e.BTN_SOUTH, 1)
        self.event(e.EV_KEY, e.BTN_TL2, 1)
        self.assertEqual(self.output.events[:2], [(e.EV_KEY, e.BTN_LEFT, 1), (e.EV_KEY, e.BTN_LEFT, 0)])
    def test_window_focus_once_until_centered(self):
        self.event(e.EV_KEY, e.BTN_TL2, 1)
        self.event(e.EV_ABS, e.ABS_X, 255)
        self.desktop.tick(0, .016); self.desktop.tick(.016, .016)
        self.assertEqual(self.output.events.count((e.EV_KEY, e.KEY_RIGHT, 1)), 1)
        self.event(e.EV_ABS, e.ABS_X, 128)
        self.desktop.tick(.032, .016)
        self.event(e.EV_ABS, e.ABS_X, 255)
        self.desktop.tick(.048, .016)
        self.assertEqual(self.output.events.count((e.EV_KEY, e.KEY_RIGHT, 1)), 2)
    @patch.object(controller, 'notify')
    def test_ps_hold_toggles_and_releases(self, _):
        self.event(e.EV_KEY, e.BTN_SOUTH, 1)
        self.event(e.EV_KEY, e.BTN_MODE, 1)
        self.desktop.tick(1.1, .016)
        self.assertFalse(self.desktop.enabled)
        self.assertIn((e.EV_KEY, e.BTN_LEFT, 0), self.output.events)
        self.desktop.tick(2, .016)
        self.assertFalse(self.desktop.enabled)
    @patch.object(controller.subprocess, 'Popen')
    def test_keyboard_shortcut_toggles(self, popen):
        process = popen.return_value
        process.poll.return_value = None
        self.event(e.EV_KEY, e.BTN_TL2, 1)
        self.event(e.EV_KEY, e.BTN_THUMBR, 1)
        popen.assert_called_once()
        self.event(e.EV_KEY, e.BTN_THUMBR, 0)
        self.event(e.EV_KEY, e.BTN_THUMBR, 1)
        process.terminate.assert_called_once()

    def test_close_requires_both_triggers_held(self):
        self.event(e.EV_KEY, e.BTN_TL2, 1)
        self.event(e.EV_KEY, e.BTN_TR2, 1, 1.0)
        self.desktop.tick(1.7, .016)
        self.assertNotIn((e.EV_KEY, e.KEY_W, 1), self.output.events)
        self.desktop.tick(1.81, .016)
        self.desktop.tick(2.0, .016)
        self.assertEqual(self.output.events.count((e.EV_KEY, e.KEY_W, 1)), 1)
        self.assertIn((e.EV_KEY, e.KEY_LEFTMETA, 1), self.output.events)

    def test_close_cancels_on_trigger_release(self):
        self.event(e.EV_KEY, e.BTN_TL2, 1)
        self.event(e.EV_KEY, e.BTN_TR2, 1, 1.0)
        self.event(e.EV_KEY, e.BTN_TR2, 0, 1.2)
        self.desktop.tick(2.0, .016)
        self.assertNotIn((e.EV_KEY, e.KEY_W, 1), self.output.events)

    def test_remapped_shortcut_reloads_without_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(controller.shortcuts, 'CONFIG', Path(temp) / 'shortcuts.json'):
                values = controller.shortcuts.DEFAULTS.copy()
                values['layer_cross'] = 'CTRL+ALT+T'
                controller.shortcuts.save(values)
                self.desktop.reload_config()
                self.event(e.EV_KEY, e.BTN_TL2, 1)
                self.event(e.EV_KEY, e.BTN_SOUTH, 1)
                self.assertEqual(self.output.events, [
                    (e.EV_KEY, e.KEY_LEFTCTRL, 1), (e.EV_KEY, e.KEY_LEFTALT, 1),
                    (e.EV_KEY, e.KEY_T, 1), (e.EV_KEY, e.KEY_T, 0),
                    (e.EV_KEY, e.KEY_LEFTALT, 0), (e.EV_KEY, e.KEY_LEFTCTRL, 0)])

    def test_invalid_config_does_not_replace_active_shortcuts(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(controller.shortcuts, 'CONFIG', Path(temp) / 'shortcuts.json'):
                controller.shortcuts.CONFIG.write_text('{"layer_cross": "SUPER+NOT_A_KEY"}')
                self.desktop.reload_config()
                self.assertEqual(self.desktop.bindings['layer_cross'], 'SUPER+SPACE')

    def test_r1_holds_f9_for_push_to_talk(self):
        self.event(e.EV_KEY, e.BTN_TR, 1)
        self.event(e.EV_KEY, e.BTN_TR, 0)
        self.assertEqual(self.output.events, [(e.EV_KEY, e.KEY_F9, 1), (e.EV_KEY, e.KEY_F9, 0)])

    def test_deadzone_and_pointer(self):
        self.desktop.tick(0, .016)
        self.assertEqual(self.output.events, [])
        self.event(e.EV_ABS, e.ABS_X, 255)
        self.desktop.tick(.016, .016)
        self.assertTrue(any(x[0] == e.EV_REL and x[1] == e.REL_X and x[2] > 0 for x in self.output.events))
    def test_hat_releases(self):
        self.event(e.EV_ABS, e.ABS_HAT0Y, -1)
        self.event(e.EV_ABS, e.ABS_HAT0Y, 0)
        self.assertEqual(self.output.events, [(e.EV_KEY, e.KEY_UP, 1), (e.EV_KEY, e.KEY_UP, 0)])

if __name__ == '__main__': unittest.main()
