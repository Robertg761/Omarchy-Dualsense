#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python -c 'import evdev, gi; gi.require_version("Gtk", "4.0"); gi.require_version("Gtk4LayerShell", "1.0")' || { echo 'Install python-evdev, python-gobject, gtk4 and gtk4-layer-shell first.' >&2; exit 1; }
test -w /dev/uinput || { echo 'Cannot write /dev/uinput. Configure device permissions for your user first.' >&2; exit 1; }
unit_path="$HOME/.config/systemd/user/omarchy-dualsense.service"
if [[ -e "$unit_path" ]] && ! cmp -s systemd/omarchy-dualsense.service "$unit_path"; then
  echo "Refusing to overwrite a modified service file: $unit_path" >&2
  echo 'Review and move it aside before installing.' >&2
  exit 1
fi
plugin_dir="$HOME/.config/omarchy/plugins/io.github.robertg761.dualsense"
if [[ "$(pwd -P)" != "$(realpath -m "$plugin_dir")" && ! -e "$plugin_dir/.git" ]]; then
  for file in manifest.json Service.qml; do
    if [[ -e "$plugin_dir/$file" ]] && ! cmp -s "$file" "$plugin_dir/$file"; then
      echo "Refusing to overwrite an existing plugin file: $plugin_dir/$file" >&2
      exit 1
    fi
  done
fi
install -d "$HOME/.local/share/omarchy-dualsense" "$HOME/.config/systemd/user"
install -m 755 dualsense/controller.py dualsense/keyboard.py dualsense/menu.py dualsense/keybindings.sh dualsense/config.py "$HOME/.local/share/omarchy-dualsense/"
install -m 644 systemd/omarchy-dualsense.service "$HOME/.config/systemd/user/"
# A git-managed plugin checkout already contains the shell files. For a local
# development checkout, install only the shell entry point into Omarchy's plugin directory.
if [[ "$(pwd -P)" != "$(realpath -m "$plugin_dir")" ]]; then
  if [[ -e "$plugin_dir/.git" ]]; then
    echo "Using existing git-managed plugin at $plugin_dir"
  else
    install -d "$plugin_dir"
    install -m 644 manifest.json Service.qml "$plugin_dir/"
  fi
fi
systemctl --user daemon-reload
systemctl --user enable --now omarchy-dualsense.service
systemctl --user restart omarchy-dualsense.service
if command -v omarchy-shell >/dev/null && command -v omarchy >/dev/null; then
  omarchy-shell shell rescanPlugins >/dev/null || true
  if ! omarchy plugin enable io.github.robertg761.dualsense; then
    echo 'The service is installed, but the shell plugin could not be enabled. Run: omarchy plugin enable io.github.robertg761.dualsense' >&2
    exit 1
  fi
fi
