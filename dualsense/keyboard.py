#!/usr/bin/env python3
"""Simple controller-clickable keyboard that keeps focus on the active app."""
import os
import sys
import ctypes.util

# Layer shell must load before GTK's Wayland client library.
if not os.environ.get('DUALSENSE_LAYER_PRELOADED'):
    library = ctypes.util.find_library('gtk4-layer-shell')
    if library:
        env = os.environ.copy()
        env['LD_PRELOAD'] = ':'.join(filter(None, (library, env.get('LD_PRELOAD', ''))))
        env['DUALSENSE_LAYER_PRELOADED'] = '1'
        os.execvpe(sys.executable, [sys.executable, __file__, *sys.argv[1:]], env)
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, Gtk4LayerShell as layer
from evdev import UInput, ecodes as e

ROWS = [
    [('1','KEY_1'),('2','KEY_2'),('3','KEY_3'),('4','KEY_4'),('5','KEY_5'),('6','KEY_6'),('7','KEY_7'),('8','KEY_8'),('9','KEY_9'),('0','KEY_0'),('-', 'KEY_MINUS'),('=', 'KEY_EQUAL'),('Backspace','KEY_BACKSPACE')],
    [('Tab','KEY_TAB')] + [(c, 'KEY_'+c.upper()) for c in 'qwertyuiop'] + [('[','KEY_LEFTBRACE'),(']','KEY_RIGHTBRACE')],
    [(c, 'KEY_'+c.upper()) for c in 'asdfghjkl'] + [(';','KEY_SEMICOLON'),("'",'KEY_APOSTROPHE'),('Enter','KEY_ENTER')],
    [('Shift', None)] + [(c, 'KEY_'+c.upper()) for c in 'zxcvbnm'] + [(',', 'KEY_COMMA'),('.', 'KEY_DOT'),('/', 'KEY_SLASH')],
    [('Ctrl', None), ('Alt', None), ('Super', None), ('Space','KEY_SPACE'), ('←','KEY_LEFT'), ('↓','KEY_DOWN'), ('↑','KEY_UP'), ('→','KEY_RIGHT'), ('Close', None)],
]
MODS = {'Shift': e.KEY_LEFTSHIFT, 'Ctrl': e.KEY_LEFTCTRL, 'Alt': e.KEY_LEFTALT, 'Super': e.KEY_LEFTMETA}

class Keyboard(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.omarchy.DualSenseKeyboard')
        self.modifiers = set()
        codes = [getattr(e, name) for row in ROWS for _, name in row if name] + list(MODS.values())
        self.output = UInput({e.EV_KEY: list(set(codes))}, name='Omarchy DualSense On-screen Keyboard')

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self, title='DualSense keyboard')
        layer.init_for_window(window)
        layer.set_layer(window, layer.Layer.TOP)
        layer.set_anchor(window, layer.Edge.BOTTOM, True)
        layer.set_keyboard_mode(window, layer.KeyboardMode.NONE)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_start(10); box.set_margin_end(10); box.set_margin_top(8); box.set_margin_bottom(8)
        for row in ROWS:
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3, homogeneous=True)
            for label, name in row:
                button = Gtk.ToggleButton(label=label) if label in MODS else Gtk.Button(label=label)
                button.connect('clicked', self.clicked, label, name, window)
                line.append(button)
            box.append(line)
        window.set_child(box)
        window.present()

    def clicked(self, button, label, name, window):
        if label == 'Close':
            window.close()
            return
        if label in MODS:
            if button.get_active(): self.modifiers.add(MODS[label])
            else: self.modifiers.discard(MODS[label])
            return
        code = getattr(e, name)
        for modifier in sorted(self.modifiers): self.output.write(e.EV_KEY, modifier, 1)
        self.output.write(e.EV_KEY, code, 1); self.output.write(e.EV_KEY, code, 0)
        for modifier in sorted(self.modifiers, reverse=True): self.output.write(e.EV_KEY, modifier, 0)
        self.output.syn()

    def do_shutdown(self):
        self.output.close()
        Gtk.Application.do_shutdown(self)

if __name__ == '__main__':
    Keyboard().run(None)
