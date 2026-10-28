#!/usr/bin/env python3
"""Controller rows and shortcut editing for Omarchy's keybindings menu."""
import argparse
import os
import shlex
import subprocess
import sys
import config


def label(slot):
    name = slot.replace('layer_', 'L2 + ').replace('dpad_', 'D-pad ').replace('stick_', 'left stick ').replace('_', ' ')
    return name + (' (hold)' if slot == 'layer_r2' else '')


def records():
    values = config.load()
    command = shlex.join([sys.executable, os.path.abspath(__file__)])
    for slot, value in values.items():
        display = f'Controller {label(slot):<22} → {value or "Disabled"}  [edit]'
        print(f'{display}\texec\t{command} --edit {shlex.quote(slot)}')


def select(prompt, options):
    result = subprocess.run(['omarchy-menu-select', prompt, *options, '--', '--width', '700', '--height', '500'],
                            text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def edit(slot):
    if slot not in config.DEFAULTS:
        raise ValueError('Unknown controller input')
    values = config.load()
    current = values[slot] or 'Disabled'
    default = config.DEFAULTS[slot] or 'Disabled'
    choice = select(f'Controller {label(slot)}  •  {current}',
                    ['Change shortcut', 'Disable shortcut', f'Restore default: {default}'])
    if not choice:
        return
    if choice == 'Change shortcut':
        result = subprocess.run(['omarchy-menu-input', 'Shortcut (e.g. SUPER+W, or KEYBOARD)', '--width', '700'],
                                text=True, capture_output=True)
        if result.returncode:
            return
        value = result.stdout.strip().upper()
    elif choice == 'Disable shortcut':
        value = ''
    else:
        value = config.DEFAULTS[slot]
    try:
        config.parse(value)
        values[slot] = value
        config.save(values)
    except (OSError, ValueError) as exc:
        subprocess.run(['notify-send', '-a', 'DualSense', 'Could not save controller shortcut', str(exc)], check=False)
        return
    subprocess.run(['notify-send', '-a', 'DualSense', 'Controller shortcut saved',
                    f'{label(slot)}: {value or "Disabled"}'], check=False)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--records', action='store_true')
    group.add_argument('--edit')
    args = parser.parse_args()
    try:
        records() if args.records else edit(args.edit)
    except (OSError, ValueError) as exc:
        print(f'DualSense shortcuts: {exc}', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
