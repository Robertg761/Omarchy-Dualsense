# Marketplace submission draft

This is a draft, not a submitted issue. The repository URL and ownership confirmations must be filled in after the repository is public. Review the final title, body and checklist before submission.

**Title:** `[Plugin]: DualSense desktop control`

### Repository URL

<public GitHub repository URL>

### Category

Hardware

### Tags

hyprland, games, workspaces

### Suggest a missing tag

_No response_

### Maintainer notes

Please apply the `manual-setup` label. The standard Omarchy plugin installation only installs the shell manifest; desktop control requires the documented, separately invoked `install.sh` and the listed Python, GTK and input-device permissions. The keybindings menu integration requires a separate, documented user configuration step. The service reads DualSense input devices and creates virtual keyboard and mouse devices through uinput. The physical controller remains available to games; holding PS turns the desktop mappings off.

USB has been detected on the developer's system. Bluetooth, DualSense Edge and a fresh installation on another system have not yet been verified.

### Submission checklist

- [ ] The repository is public and contains installation and removal instructions.
- [ ] I have documented the plugin license and any external dependencies.
- [ ] I confirm that I own or have permission to submit this plugin and its preview assets.
- [ ] The plugin does not overwrite user configuration without explicit consent.
- [ ] I understand that approval is for listing and is not a security review.
