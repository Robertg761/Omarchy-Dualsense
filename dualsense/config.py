"""Shortcut definitions and validation shared by the service and settings app."""
import json
import os
from pathlib import Path
import tempfile
from evdev import ecodes as e

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'omarchy-dualsense' / 'shortcuts.json'
BUTTONS = {
    e.BTN_SOUTH: 'cross', e.BTN_EAST: 'circle', e.BTN_NORTH: 'square',
    e.BTN_WEST: 'triangle', e.BTN_TL: 'l1', e.BTN_TR: 'r1',
    e.BTN_TR2: 'r2', e.BTN_SELECT: 'create', e.BTN_START: 'options',
    e.BTN_THUMBL: 'l3', e.BTN_THUMBR: 'r3',
}
DEFAULTS = {
    'cross': 'MOUSE_LEFT', 'circle': 'MOUSE_RIGHT', 'square': 'BACKSPACE',
    'triangle': 'TAB', 'l1': 'SUPER+SHIFT+TAB', 'r1': 'F9',
    'r2': '', 'create': 'ESC', 'options': 'ENTER', 'l3': '', 'r3': '',
    'dpad_left': 'LEFT', 'dpad_right': 'RIGHT', 'dpad_up': 'UP', 'dpad_down': 'DOWN',
    'layer_cross': 'SUPER+SPACE', 'layer_circle': 'ESC', 'layer_square': 'SUPER+T',
    'layer_triangle': 'SUPER+F', 'layer_l1': 'SUPER+SHIFT+TAB', 'layer_r1': 'SUPER+TAB',
    'layer_r2': 'SUPER+W', 'layer_create': 'SUPER+S', 'layer_options': 'SUPER+K',
    'layer_l3': '', 'layer_r3': 'KEYBOARD',
    'layer_dpad_left': 'SUPER+SHIFT+LEFT', 'layer_dpad_right': 'SUPER+SHIFT+RIGHT',
    'layer_dpad_up': 'SUPER+SHIFT+UP', 'layer_dpad_down': 'SUPER+SHIFT+DOWN',
    'layer_stick_left': 'SUPER+LEFT', 'layer_stick_right': 'SUPER+RIGHT',
    'layer_stick_up': 'SUPER+UP', 'layer_stick_down': 'SUPER+DOWN',
}
ALIASES = {'SUPER': 'LEFTMETA', 'META': 'LEFTMETA', 'SHIFT': 'LEFTSHIFT',
           'CTRL': 'LEFTCTRL', 'CONTROL': 'LEFTCTRL', 'ALT': 'LEFTALT',
           'ESCAPE': 'ESC', 'RETURN': 'ENTER'}
SPECIAL = {'MOUSE_LEFT': e.BTN_LEFT, 'MOUSE_RIGHT': e.BTN_RIGHT, 'MOUSE_MIDDLE': e.BTN_MIDDLE}


def parse(value):
    if not isinstance(value, str):
        raise ValueError('Shortcut must be text')
    value = value.strip().upper()
    if value in ('', 'KEYBOARD'):
        return value
    parts = value.split('+')
    if any(not part.strip() for part in parts) or len(parts) > 5:
        raise ValueError('Use keys separated by +, for example SUPER+W')
    keys = []
    for part in parts:
        token = part.strip()
        if token in SPECIAL:
            if len(parts) != 1:
                raise ValueError('Mouse buttons cannot be combined with keys')
            return (SPECIAL[token],)
        token = token.removeprefix('KEY_')
        token = ALIASES.get(token, token)
        code = getattr(e, 'KEY_' + token, None)
        if not isinstance(code, int) or token in ('RESERVED', 'MAX', 'CNT'):
            raise ValueError(f'Unknown key: {part.strip()}')
        keys.append(code)
    if len(set(keys)) != len(keys):
        raise ValueError('A key may appear only once')
    return tuple(keys)


def load():
    try:
        data = json.loads(CONFIG.read_text())
    except FileNotFoundError:
        return DEFAULTS.copy()
    if not isinstance(data, dict) or set(data) - set(DEFAULTS):
        raise ValueError('Invalid shortcut configuration')
    result = {**DEFAULTS, **data}
    for value in result.values():
        parse(value)
    return result


def save(values):
    if set(values) != set(DEFAULTS):
        raise ValueError('Shortcut configuration is incomplete')
    for value in values.values():
        parse(value)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.shortcuts-', dir=CONFIG.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(values, f, indent=2)
            f.write('\n')
        os.replace(name, CONFIG)
    finally:
        if os.path.exists(name):
            os.unlink(name)
