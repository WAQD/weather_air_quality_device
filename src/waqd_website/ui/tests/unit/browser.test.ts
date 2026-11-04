import { describe, it, expect } from 'vitest'
import { isWindowsFirefox } from '../../src/utils/browser'

describe('isWindowsFirefox', () => {
  it('matches Firefox on Windows', () => {
    expect(
      isWindowsFirefox(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
      ),
    ).toBe(true)
  })

  it('does not match Firefox on Linux', () => {
    expect(
      isWindowsFirefox(
        'Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
      ),
    ).toBe(false)
  })

  it('does not match Chromium browsers on Windows', () => {
    expect(
      isWindowsFirefox(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
      ),
    ).toBe(false)
    expect(
      isWindowsFirefox(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
      ),
    ).toBe(false)
  })

  it('does not match Firefox on macOS or Android', () => {
    expect(
      isWindowsFirefox(
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0',
      ),
    ).toBe(false)
    expect(
      isWindowsFirefox(
        'Mozilla/5.0 (Android 14; Mobile; rv:141.0) Gecko/141.0 Firefox/141.0',
      ),
    ).toBe(false)
  })
})
