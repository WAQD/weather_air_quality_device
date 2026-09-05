mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/set-default-audio-volume.service <<'EOF'
[Unit]
Description=Set default audio volume for PipeWire (user)
After=pipewire.service pipewire-pulse.service
Wants=pipewire.service pipewire-pulse.service

[Service]
Type=oneshot
ExecStart=/usr/bin/pactl set-sink-volume @DEFAULT_SINK@ 100%
ExecStart=/usr/bin/pactl set-sink-mute @DEFAULT_SINK@ 0

[Install]
WantedBy=default.target
EOF

# systemctl --user requires a running user systemd manager. That manager
# is normally started by the desktop session (lightdm -> lxsession) at
# graphical login. The installer can run before that (e.g. SSH install,
# or the headless test container), so systemctl --user fails with
# "Process org.freedesktop.systemd1 exited with status 1". The unit file
# itself is already on disk, so we just symlink-enable it for the next
# login and tolerate the daemon-reload failure.
#
# `systemctl --user enable --now` requires a running user manager; the
# symlink alone is enough - the unit gets picked up at the next login.
if systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user daemon-reload
fi

# Symlink-enable (no --user needed, writes directly to ~/.config/systemd/user/default.target.wants/).
unit_dir=~/.config/systemd/user
target_dir="$unit_dir/default.target.wants"
mkdir -p "$target_dir"
ln -sf "../set-default-audio-volume.service" "$target_dir/set-default-audio-volume.service"
echo "# Audio volume unit installed; will activate on next user login."