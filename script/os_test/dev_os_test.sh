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
#   WAQD_NSPAWN_MNT=...          persistent prepared RPi rootfs directory
#   WAQD_KEEP_MOUNT=1            preserve that rootfs after the run
#   WAQD_OS_TEST_SKIP_INSTALL=1  validate an existing RPi installation

set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"

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
            IMAGE=$(./script/os_test/fetch_rpios_image.sh "$WAQD_RPIOS_CACHE_DIR" | tail -n 1)
            else
            IMAGE=$(./script/os_test/fetch_rpios_image.sh | tail -n 1)
            fi
        fi
        if [ ! -f "$IMAGE" ]; then
            echo "ERROR: RPi OS image does not exist: $IMAGE" >&2
            exit 1
        fi
        command -v sudo >/dev/null || { echo "ERROR: sudo is required" >&2; exit 1; }
        sudo -v

        MACHINE="${WAQD_OS_TEST_MACHINE:-waqd-os-test}"
        NSPAWN_LOG="${WAQD_NSPAWN_LOG:-/tmp/${MACHINE}-nspawn.log}"
        echo "Using RPi OS image: $IMAGE"
        echo "Starting nspawn machine '$MACHINE' (log: $NSPAWN_LOG)"
        sudo -n ./script/os_test/run_nspawn.sh "$IMAGE" "$MACHINE" \
            >"$NSPAWN_LOG" 2>&1 &
        NSPAWN_PID=$!
        cleanup() {
            if machinectl show "$MACHINE" >/dev/null 2>&1; then
                sudo -n machinectl poweroff "$MACHINE" >/dev/null 2>&1 || true
            fi
            kill "$NSPAWN_PID" 2>/dev/null || true
        }
        trap cleanup EXIT INT TERM

        echo "Waiting for nspawn machine '$MACHINE'..."
        for _ in $(seq 1 "${WAQD_NSPAWN_START_TIMEOUT:-180}"); do
            if machinectl show "$MACHINE" >/dev/null 2>&1; then
                break
            fi
            if ! kill -0 "$NSPAWN_PID" 2>/dev/null; then
                cat "$NSPAWN_LOG" >&2 || true
                echo "ERROR: nspawn exited before becoming ready" >&2
                exit 1
            fi
            sleep 1
        done
        machinectl show "$MACHINE" >/dev/null 2>&1 || {
            echo "ERROR: nspawn did not become ready; see $NSPAWN_LOG" >&2
            exit 1
        }

        export WAQD_OS_TEST=1
        export WAQD_OS_TEST_MACHINE="$MACHINE"
        set +e
        pdm run pytest test/os_test/test_install_rpios.py -s \
            --timeout="${WAQD_TEST_TIMEOUT:-3600}" "${@:2}"
        TEST_STATUS=$?
        set -e
        exit "$TEST_STATUS"
        ;;
    *)
        echo "Usage: $0 [debian|rpios] [pytest arguments...]" >&2
        exit 2
        ;;
esac