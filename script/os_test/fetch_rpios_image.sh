#!/bin/bash
# Download the OFFICIAL Raspberry Pi OS image and verify its checksum.
#
# No unofficial base image is used anywhere: the real image is downloaded from
# downloads.raspberrypi.org and later mounted directly (see run_nspawn.sh).
#
# Usage:
#   ./script/os_test/fetch_rpios_image.sh [output_dir]
#
# Env:
#   RPIOS_URL  - override the image URL
#   RPIOS_FLAVOR - official image index suffix (default: arm64 desktop)
#   RPIOS_REFRESH=1 - ignore cached metadata and resolve/download again

set -euo pipefail

OUT_DIR="${1:-$HOME/.cache/waqd-os-test}"
mkdir -p "$OUT_DIR"
FLAVOR="${RPIOS_FLAVOR:-arm64}"
INDEX_URL="https://downloads.raspberrypi.org/raspios_${FLAVOR}/images/"

if [ "${RPIOS_REFRESH:-0}" != "1" ] && [ -f "$OUT_DIR/current-image" ]; then
    CACHED_IMG=$(cat "$OUT_DIR/current-image")
    if [ -f "$CACHED_IMG" ]; then
        echo "Using cached image: $CACHED_IMG" >&2
        echo "$CACHED_IMG"
        exit 0
    fi
fi

# Resolve the latest image if no explicit URL is given.
if [ -z "${RPIOS_URL:-}" ]; then
    echo "Resolving latest image from $INDEX_URL" >&2
    # Directory listing -> newest <date>-raspios-.../ dir -> the .img.xz inside it
    LATEST_DIR=$(curl -fsSL "$INDEX_URL" \
        | grep -o "raspios_${FLAVOR}-[0-9-]*/" \
        | sort -u | tail -n1)
    if [ -z "$LATEST_DIR" ]; then
        echo "ERROR: could not resolve the latest image directory" >&2
        exit 1
    fi
    IMG_NAME=$(curl -fsSL "${INDEX_URL}${LATEST_DIR}" \
        | grep -o "[0-9-]*-raspios[^\"<>]*\.img\.xz" \
        | sort -u | tail -n1)
    if [ -z "$IMG_NAME" ]; then
        echo "ERROR: could not resolve the image name in ${LATEST_DIR}" >&2
        exit 1
    fi
    RPIOS_URL="${INDEX_URL}${LATEST_DIR}${IMG_NAME}"
fi

IMG_XZ="$OUT_DIR/$(basename "$RPIOS_URL")"
IMG="${IMG_XZ%.xz}"

if [ -f "$IMG" ]; then
    echo "Image already present: $IMG" >&2
    printf '%s\n' "$IMG" > "$OUT_DIR/current-image"
    echo "$IMG"
    exit 0
fi

echo "Downloading $RPIOS_URL" >&2
curl -fL --progress-bar -o "$IMG_XZ" "$RPIOS_URL"

# Verify against the published SHA-256 next to the image.
echo "Verifying checksum..." >&2
EXPECTED=$(curl -fsSL "${RPIOS_URL}.sha256" | awk '{print $1}')
ACTUAL=$(sha256sum "$IMG_XZ" | awk '{print $1}')
if [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "ERROR: checksum mismatch" >&2
    echo "  expected: $EXPECTED" >&2
    echo "  actual:   $ACTUAL" >&2
    exit 1
fi
echo "Checksum OK" >&2

echo "Decompressing..." >&2
xz -d -T0 -k "$IMG_XZ" 2>/dev/null || xz -d -k "$IMG_XZ"

printf '%s\n' "$IMG" > "$OUT_DIR/current-image"
echo "$IMG"
