#!/bin/bash
# Development fast lane for the OS-level tests.
#
# It performs the setup normally done in separate terminals, while preserving
# caches. CI should invoke pytest directly instead of using this interactive
# helper.
#
# Usage:
#   ./script/os_test/dev_os_test.sh debian
#   ./script/os_test/dev_os_test.sh rpios
#
# Useful environment variables:
#   WAQD_OS_TEST_REBUILD=1       rebuild the Debian base image
#   RPIOS_REFRESH=1              resolve/download a new RPi OS image
#   WAQD_QEMU_APPEND=...         guest kernel command line
#
# Run ./script/os_test/setup_qemu.sh first for the complete QEMU setup.
#   WAQD_OS_TEST_SKIP_INSTALL=1  validate an existing RPi installation

set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"

# Always execute this Bash script with Bash, regardless of the caller's shell.
# Do not use Fish syntax here; this file is also the single entry point for
# commands that need to run under the repository's Python environment.

if [ "${CI:-}" = "1" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo "ERROR: dev_os_test.sh is for local development, not CI." >&2
    echo "Run the appropriate pytest command directly in CI." >&2
    exit 2
fi

TIER="${1:-debian}"
case "$TIER" in
    debian)
        exec env WAQD_OS_TEST=1 pdm run pytest \
            test/os_test/test_install_debian.py -s --timeout="${WAQD_TEST_TIMEOUT:-1800}" \
            "${@:2}"
        ;;
    rpios)
        IMAGE="${WAQD_RPIOS_IMAGE:-}"
        if [ -z "$IMAGE" ]; then
            if [ -n "${WAQD_RPIOS_CACHE_DIR:-}" ]; then
                IMAGE=$(./script/os_test/fetch_rpios_image.sh "$WAQD_RPIOS_CACHE_DIR")
            else
                IMAGE=$(./script/os_test/fetch_rpios_image.sh)
            fi
        fi
        if [ ! -f "$IMAGE" ]; then
            echo "ERROR: RPi OS image does not exist: $IMAGE" >&2
            exit 1
        fi
        command -v sudo >/dev/null || { echo "ERROR: sudo is required" >&2; exit 1; }
        sudo -v

        export WAQD_OS_TEST=1
        export WAQD_RPIOS_IMAGE="$IMAGE"
        export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
        exec pdm run pytest test/os_test/test_install_rpios.py -s \
            --timeout="${WAQD_TEST_TIMEOUT:-3600}" "${@:2}"
        ;;
    *)
        echo "Usage: $0 [debian|rpios] [pytest arguments...]" >&2
        exit 2
        ;;
esac