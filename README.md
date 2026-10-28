# Omarchy DualSense

Use a PS5 DualSense controller to operate an Omarchy desktop. An Omarchy plugin adds editable entries to the keybindings menu, and a user-session service translates controller input into a virtual keyboard and mouse. The controller touchpad remains available as a normal touchpad.

## Default controls

| Input | Action |
| --- | --- |
| Left stick | Move pointer |
| Right stick | Scroll |
| Cross / Circle | Left / right mouse button, including click and drag |
| Square / Triangle | Backspace / Tab |
| D-pad | Arrow keys |
| Options / Create | Enter / Escape |
| L1 | Previous workspace |
| R1 | Hold for voice dictation (F9 push-to-talk) |
| Hold L2 + R1 | Next workspace |
| Hold L2 + left stick | Focus window in that direction; return stick to center between moves |
| Hold L2 + D-pad | Swap focused window in that direction |
| Hold L2 + Cross | Open Omarchy menu |
| Hold L2 + Triangle | Toggle fullscreen |
| Hold L2 + Square | Toggle floating window |
| Hold L2 + Circle | Escape |
| Hold L2 + Options / Create | Open keybindings / toggle scratchpad |
| Hold L2 + click right stick (R3) | Show or hide on-screen keyboard |
| Hold L2, then hold R2 for 0.8 seconds | Close the focused window (Super + W) |
| Hold PS for one second | Turn desktop controls off or on |

The on-screen keyboard uses the pointer and Cross. Shift, Ctrl, Alt, and Super are sticky toggles: click each again to turn it off. The keyboard sends keys to the focused application without taking keyboard focus. Close it with L2 + R3 or its Close button. It uses the current keyboard layout.

The PS switch disables only this project's desktop translations. The physical gamepad remains visible to games and applications at all times, so turn desktop controls off while playing. The switch is remembered across a controller reconnect during the current service run; it resets to on when the service restarts. If Steam or another program also maps controller input to the desktop, disable its mapping to avoid duplicate actions.

## Configure shortcuts

Open the Omarchy **Keybindings** menu with Super + K and search for `Controller`. Select a controller entry to change it, disable it, or restore its default. Enter names such as `SUPER+W`, `CTRL+SHIFT+T`, `F11`, or `SPACE`. `MOUSE_LEFT`, `MOUSE_RIGHT`, `MOUSE_MIDDLE`, and `KEYBOARD` are also available. A saved change applies to the running service within one second.

Buttons, D-pad directions, and L2 plus left-stick directions are configurable, including the keyboard toggle and the delayed L2 + R2 action. L2 remains the layer selector and holding PS remains the on/off switch. Normal left-stick pointer movement and right-stick scrolling are fixed. The on-screen keyboard can be used to enter shortcut names.

Your shortcuts live in `~/.config/omarchy-dualsense/shortcuts.json` (or `$XDG_CONFIG_HOME/omarchy-dualsense/shortcuts.json`). Plugin updates and uninstall leave this file alone. Invalid saved shortcuts do not replace the running mappings.

## Setup

Requirements: Omarchy with Hyprland, Python, `python-evdev`, `python-gobject`, `gtk4`, `gtk4-layer-shell`, a running user systemd session, and permission to read the controller's `/dev/input/event*` node and write `/dev/uinput`. A DualSense or DualSense Edge should be recognized by Linux's `hid-playstation` driver. USB and Bluetooth use the same discovery path, but Bluetooth and DualSense Edge need additional hardware testing.

For a local checkout, run:

```sh
./install.sh
```

For a shared Git repository, set `REPOSITORY_URL` to its published GitHub URL, add it with Omarchy's plugin manager, then run setup from the installed checkout:

```sh
omarchy plugin add "$REPOSITORY_URL" --enable
cd ~/.config/omarchy/plugins/io.github.robertg761.dualsense
./install.sh
```

Omarchy's plugin installer does not run scripts or install dependencies. The separate setup command installs the Python programs in `~/.local/share/omarchy-dualsense/`, registers the shell plugin, and enables the user service. Re-run it after updating the repository. It does not change your Hyprland configuration or existing input-remapper presets, and refuses to overwrite a modified service unit or unrelated local plugin files. If setup reports that the shell is not responding, retry `omarchy plugin enable io.github.robertg761.dualsense` once the graphical session is ready.

```sh
systemctl --user status omarchy-dualsense.service
journalctl --user -u omarchy-dualsense.service -f
systemctl --user stop omarchy-dualsense.service
systemctl --user start omarchy-dualsense.service
./uninstall.sh
```

Omarchy's stock keybindings list currently has no extension API for extra editable rows. To add the rows to a stock setup, bind Super + K to the provided menu wrapper in `~/.config/hypr/bindings.lua`:

```lua
hl.unbind("SUPER + K")
o.bind("SUPER + K", "Keybindings", os.getenv("HOME") .. "/.local/share/omarchy-dualsense/keybindings.sh")
```

This replaces the existing Super + K binding. Check `omarchy menu keybindings --print` first and preserve any personal menu wrapper you already use. If you already have a custom wrapper, add the output of `~/.local/share/omarchy-dualsense/menu.py --records` to its tab-separated records and keep its existing selection and dispatch behavior. The included wrapper sources Omarchy's menu implementation, so future Omarchy changes to its internal shell functions may require an update. Remove the added binding from `bindings.lua` when uninstalling the wrapper. The installer does not overwrite Hyprland bindings or existing menu extensions.

The mappings use Omarchy's default shortcuts, so customized or disabled shortcuts can change the resulting actions. The controller must be connected to a running desktop session; the service waits for it and reconnects automatically. Existing keyboard and mouse remain usable. The on-screen keyboard is for the unlocked desktop and is not a login or lock-screen keyboard.

## Testing

```sh
python -m unittest discover -s tests -v
```

The unit tests cover the control state machine. Real controller testing is needed for feel, pointer speed, touchpad behavior, game compatibility, and Bluetooth reconnects.

## License

[MIT](LICENSE).
