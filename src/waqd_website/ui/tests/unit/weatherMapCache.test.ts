import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@openmeteo/weather-map-layer', () => ({
  omProtocol: vi.fn(),
}))

import { omProtocol } from '@openmeteo/weather-map-layer'
import { cachedOmProtocol, clearWeatherMapCache } from '../../src/utils/weatherMapCache'

const mockedOmProtocol = vi.mocked(omProtocol)

describe('weatherMapCache', () => {
  beforeEach(() => {
    clearWeatherMapCache()
    mockedOmProtocol.mockReset()
  })

  it('serves repeat requests from cache without re-calling omProtocol', async () => {
    mockedOmProtocol.mockResolvedValue({ data: { tiles: ['a'] } })

    const params = { url: 'http://tiles.example/1' } as any
    const abort = new AbortController()

    const r1 = await cachedOmProtocol(params, abort)
    const r2 = await cachedOmProtocol(params, abort)

    expect(r1.data).toEqual({ tiles: ['a'] })
    expect(r2.data).toEqual({ tiles: ['a'] })
    expect(mockedOmProtocol).toHaveBeenCalledTimes(1)
  })

  it('returns a shallow copy so callers cannot mutate the cache', async () => {
    mockedOmProtocol.mockResolvedValue({ data: { tiles: ['a'], version: 1 } })

    const params = { url: 'http://tiles.example/2' } as any
    const abort = new AbortController()

    await cachedOmProtocol(params, abort)
    const r2 = await cachedOmProtocol(params, abort)
      ; (r2.data as any).version = 999

    const r3 = await cachedOmProtocol(params, abort)
    expect((r3.data as any).version).toBe(1)
    expect(mockedOmProtocol).toHaveBeenCalledTimes(1)
  })

  it('clears the cache', async () => {
    mockedOmProtocol.mockResolvedValue({ data: { tiles: ['a'] } })

    const params = { url: 'http://tiles.example/3' } as any
    const abort = new AbortController()

    await cachedOmProtocol(params, abort)
    clearWeatherMapCache()
    await cachedOmProtocol(params, abort)

    expect(mockedOmProtocol).toHaveBeenCalledTimes(2)
  })
})
