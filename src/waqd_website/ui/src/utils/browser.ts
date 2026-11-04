/**
 * Browser/platform detection used for render workarounds.
 *
 * Keep these helpers dependency-free: they run during app bootstrap, before
 * Vue is mounted.
 */

/**
 * Firefox on Windows composites `backdrop-filter` on the CPU for large blurred
 * surfaces, which makes scrolling stutter badly. Chrome and Firefox on other
 * platforms handle the same UI fine, so the workaround is scoped to this combo.
 */
export function isWindowsFirefox(
  userAgent: string = typeof navigator !== 'undefined' ? navigator.userAgent : '',
): boolean {
  return /Windows/i.test(userAgent) && /Firefox\/\d/i.test(userAgent)
}

/**
 * Adds feature/platform classes to `<html>` so CSS can target specific engines.
 * Call this once, before mounting the app.
 */
export function applyBrowserClasses(): void {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  if (isWindowsFirefox()) {
    root.classList.add('waqd-firefox-windows')
  }
}
