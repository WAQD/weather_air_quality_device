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

systemctl --user daemon-reload
systemctl --user enable --now set-default-audio-volume.service