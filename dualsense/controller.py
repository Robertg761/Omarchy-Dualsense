#!/usr/bin/env python3
"""DualSense desktop input for an active Linux graphical session."""
import errno
import logging
import math
import os
import select
import signal
import subprocess
import time

from evdev import InputDevice, UInput, ecodes as e, list_devices
import config as shortcuts

LOG = logging.getLogger('dualsense')
SONY = 0x054c
PRODUCTS = {0x0ce6, 0x0df2}
TICK = 1 / 60
DEADZONE = 0.22
LAYER_THRESHOLD = 100


def notify(message):
    try:
        subprocess.Popen(['notify-send', '-a', 'DualSense desktop', 'DualSense desktop', message],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def find_controller():
    for path in list_devices():
        try:
            device = InputDevice(path)
            caps = device.capabilities()
            if (device.info.vendor == SONY and device.info.product in PRODUCTS
                    and e.BTN_SOUTH in caps.get(e.EV_KEY, [])
                    and any(code == e.ABS_X for code, _ in caps.get(e.EV_ABS, []))):
                return device
            device.close()
        except OSError:
            continue
    return None


def normalized(value, info):
    center = (info.max + info.min) / 2
    half = (info.max - info.min) / 2
    if not half:
        return 0.0
    value = max(-1.0, min(1.0, (value - center) / half))
    if abs(value) <= DEADZONE:
        return 0.0
    return math.copysign(((abs(value) - DEADZONE) / (1 - DEADZONE)) ** 1.6, value)


class Desktop:
    def __init__(self, output, axes, enabled=True):
        self.output = output
        self.info = axes
        self.axes = {code: info.value for code, info in axes.items()}
        self.enabled = enabled
        self.layer = False
        self.buttons = set()
        self.held = set()
        self.direction = None
        self.pointer_remainder = [0.0, 0.0]
        self.scroll_remainder = [0.0, 0.0]
        self.ps_since = None
        self.ps_used = False
        self.keyboard = None
        self.close_since = None
        self.close_used = False
        try:
            self.bindings = shortcuts.load()
        except (OSError, ValueError) as exc:
            LOG.error('Invalid shortcuts: %s; using defaults', exc)
            self.bindings = shortcuts.DEFAULTS.copy()
        self.config_stamp = self.get_config_stamp()
        self.next_config_check = 0
        self.held_slots = {}

    @staticmethod
    def get_config_stamp():
        try:
            return shortcuts.CONFIG.stat().st_mtime_ns
        except FileNotFoundError:
            return None

    def reload_config(self):
        stamp = self.get_config_stamp()
        if stamp == self.config_stamp:
            return
        try:
            bindings = shortcuts.load()
        except (OSError, ValueError) as exc:
            LOG.error('Keeping previous shortcuts: %s', exc)
            self.config_stamp = stamp
            return
        self.release_all()
        self.held_slots.clear()
        self.close_since = None
        self.bindings = bindings
        self.config_stamp = stamp
        LOG.info('Controller shortcuts reloaded')

    def action(self, slot, down=True, hold_single=False):
        if not down:
            code = self.held_slots.pop(slot, None)
            if code is not None:
                self.hold(code, False)
            return
        action = shortcuts.parse(self.bindings[slot])
        if action == 'KEYBOARD':
            self.toggle_keyboard()
        elif action:
            if hold_single and len(action) == 1:
                self.held_slots[slot] = action[0]
                self.hold(action[0], True)
            else:
                self.chord(*action)

    def emit(self, kind, code, value):
        self.output.write(kind, code, value)
        self.output.syn()

    def hold(self, code, down):
        if down and code not in self.held:
            self.emit(e.EV_KEY, code, 1)
            self.held.add(code)
        elif not down and code in self.held:
            self.emit(e.EV_KEY, code, 0)
            self.held.remove(code)

    def release_all(self):
        for code in list(self.held):
            self.hold(code, False)
        self.pointer_remainder = [0.0, 0.0]
        self.scroll_remainder = [0.0, 0.0]
        self.direction = None
        if hasattr(self, "held_slots"):
            self.held_slots.clear()

    def chord(self, *keys):
        for key in keys:
            self.emit(e.EV_KEY, key, 1)
        for key in reversed(keys):
            self.emit(e.EV_KEY, key, 0)

    def toggle_keyboard(self):
        if self.keyboard is not None and self.keyboard.poll() is None:
            self.keyboard.terminate()
            self.keyboard = None
        else:
            self.keyboard = subprocess.Popen([os.path.join(os.path.dirname(__file__), 'keyboard.py')])

    def close_keyboard(self):
        if self.keyboard is not None and self.keyboard.poll() is None:
            self.keyboard.terminate()
        self.keyboard = None

    def set_layer(self, active):
        if active != self.layer:
            self.release_all()
            self.layer = active
            self.close_since = None
            self.close_used = False

    def event(self, event, now):
        if event.type == e.EV_KEY:
            if event.value == 2:
                return
            down = event.value == 1
            if down:
                self.buttons.add(event.code)
            else:
                self.buttons.discard(event.code)
            if event.code == e.BTN_MODE:
                if down:
                    self.ps_since, self.ps_used = now, False
                else:
                    self.ps_since = None
                return
            if not self.enabled:
                return
            if event.code == e.BTN_TL2:
                self.set_layer(down or self.axes.get(e.ABS_Z, 0) >= LAYER_THRESHOLD)
                return
            if event.code == e.BTN_TR2 and self.layer:
                self.close_since = now if down else None
                self.close_used = False
                return
            slot = shortcuts.BUTTONS.get(event.code)
            if slot:
                slot = ('layer_' if self.layer else '') + slot
                self.action(slot, down, hold_single=not self.layer)
        elif event.type == e.EV_ABS:
            self.axes[event.code] = event.value
            if event.code == e.ABS_Z and self.enabled:
                self.set_layer(event.value >= LAYER_THRESHOLD or e.BTN_TL2 in self.buttons)
            if event.code in (e.ABS_HAT0X, e.ABS_HAT0Y) and self.enabled:
                self.hat(event.code, event.value)

    def hat(self, axis, value):
        pairs = {e.ABS_HAT0X: ('left', 'right'), e.ABS_HAT0Y: ('up', 'down')}
        negative, positive = pairs[axis]
        prefix = 'layer_dpad_' if self.layer else 'dpad_'
        for direction in (negative, positive):
            self.action(prefix + direction, False)
        if value:
            self.action(prefix + (negative if value < 0 else positive), hold_single=not self.layer)

    def tick(self, now, dt):
        if now >= self.next_config_check:
            self.reload_config()
            self.next_config_check = now + 1
        if self.ps_since is not None and not self.ps_used and now - self.ps_since >= 1.0:
            self.ps_used = True
            self.enabled = not self.enabled
            self.release_all()
            self.layer = False
            self.close_since = None
            notify('Desktop controls on' if self.enabled else 'Desktop controls off. Hold PS for one second to turn them on.')
        if not self.enabled:
            return
        if self.layer and self.close_since is not None and not self.close_used and now - self.close_since >= 0.8:
            self.close_used = True
            self.action('layer_r2')
        def axis(code):
            return normalized(self.axes.get(code, self.info[code].value), self.info[code])
        x, y = axis(e.ABS_X), axis(e.ABS_Y)
        if self.layer:
            magnitude = max(abs(x), abs(y))
            if magnitude < 0.35:
                self.direction = None
            elif magnitude > 0.55 and self.direction is None:
                self.direction = ('right' if x > 0 else 'left') if abs(x) > abs(y) else ('down' if y > 0 else 'up')
                self.action('layer_stick_' + self.direction)
        else:
            for index, value in enumerate((x, y)):
                self.pointer_remainder[index] += value * 1100 * dt
                amount = int(self.pointer_remainder[index])
                if amount:
                    self.pointer_remainder[index] -= amount
                    self.emit(e.EV_REL, (e.REL_X, e.REL_Y)[index], amount)
        for index, value in enumerate((axis(e.ABS_RX), -axis(e.ABS_RY))):
            self.scroll_remainder[index] += value * 10 * dt
            amount = int(self.scroll_remainder[index])
            if amount:
                self.scroll_remainder[index] -= amount
                self.emit(e.EV_REL, (e.REL_HWHEEL, e.REL_WHEEL)[index], amount)


def run():
    keys = sorted({value for name, value in vars(e).items()
                   if name.startswith('KEY_') and isinstance(value, int)
                   and name not in ('KEY_RESERVED', 'KEY_MAX', 'KEY_CNT')}
                  | set(shortcuts.SPECIAL.values()))
    capabilities = {e.EV_KEY: keys, e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL]}
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with UInput(capabilities, name='Omarchy DualSense Desktop') as output:
        enabled = True
        while running:
            device = find_controller()
            if not device:
                time.sleep(1)
                continue
            LOG.info('Connected: %s (%s)', device.name, device.path)
            axes = dict(device.capabilities(absinfo=True).get(e.EV_ABS, []))
            if not all(code in axes for code in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY)):
                device.close()
                time.sleep(1)
                continue
            desktop = Desktop(output, axes, enabled)
            notify('Controller connected. Hold PS for one second to toggle desktop controls.')
            last = time.monotonic()
            try:
                while running:
                    ready, _, _ = select.select([device.fd], [], [], TICK)
                    now = time.monotonic()
                    if ready:
                        for event in device.read():
                            desktop.event(event, now)
                    desktop.tick(now, min(now - last, 0.05))
                    last = now
            except OSError as exc:
                if exc.errno not in (errno.ENODEV, errno.EIO, errno.EBADF):
                    LOG.exception('Controller read failed')
            finally:
                enabled = desktop.enabled
                desktop.release_all()
                desktop.close_keyboard()
                device.close()
                LOG.info('Controller disconnected')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    run()
