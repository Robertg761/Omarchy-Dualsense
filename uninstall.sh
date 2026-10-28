#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if command -v omarchy >/dev/null; then
  omarchy plugin disable io.github.robertg761.dualsense 2>/dev/null || true
fi
systemctl --user disable --now omarchy-dualsense.service 2>/dev/null || true
unit_path="$HOME/.config/systemd/user/omarchy-dualsense.service"
if [[ -e "$unit_path" ]]; then
  if cmp -s systemd/omarchy-dualsense.service "$unit_path"; then
    rm "$unit_path"
  else
    echo "Preserved modified service file: $unit_path" >&2
  fi
fi
for file in controller.py keyboard.py menu.py keybindings.sh config.py; do
  rm -f "$HOME/.local/share/omarchy-dualsense/$file"
done
rmdir "$HOME/.local/share/omarchy-dualsense" 2>/dev/null || true
systemctl --user daemon-reload
plugin_dir="$HOME/.config/omarchy/plugins/io.github.robertg761.dualsense"
if [[ ! -e "$plugin_dir/.git" ]]; then
  for file in manifest.json Service.qml; do
    if [[ -e "$plugin_dir/$file" ]]; then
      if cmp -s "$file" "$plugin_dir/$file"; then
        rm "$plugin_dir/$file"
      else
        echo "Preserved modified plugin file: $plugin_dir/$file" >&2
      fi
    fi
  done
  rmdir "$plugin_dir" 2>/dev/null || true
fi
