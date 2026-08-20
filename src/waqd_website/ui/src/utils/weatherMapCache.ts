import { omProtocol } from '@openmeteo/weather-map-layer'
import type { GetResourceResponse, RequestParameters } from 'maplibre-gl'

interface CacheEntry {
    data: unknown
    size: number
}

// Decoded raster tiles are kept around so revisiting an already-played frame
// does not re-render it. ImageBitmaps are the biggest entries (width*height*4),
// so the budget bounds total retained memory.
const MAX_CACHE_BYTES = 64 * 1024 * 1024

const cache = new Map<string, CacheEntry>()
let cacheBytes = 0

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !(value instanceof ArrayBuffer)
}

function isImageBitmap(value: unknown): value is ImageBitmap {
    return typeof ImageBitmap !== 'undefined' && value instanceof ImageBitmap
}

function estimateDataSize(data: unknown): number {
    if (isImageBitmap(data)) {
        return data.width * data.height * 4
    }
    if (data instanceof ArrayBuffer) {
        return data.byteLength
    }
    if (isPlainObject(data)) {
        try {
            return JSON.stringify(data).length * 2
        } catch {
            return 0
        }
    }
    return 0
}

function store(url: string, data: unknown): void {
    if (data == null) {
        return
    }

    const size = estimateDataSize(data)
    if (size <= 0) {
        return
    }

    const existing = cache.get(url)
    if (existing) {
        cacheBytes -= existing.size
    }

    cache.delete(url)
    cache.set(url, { data, size })
    cacheBytes += size

    while (cacheBytes > MAX_CACHE_BYTES && cache.size > 1) {
        const oldestUrl = cache.keys().next().value
        if (oldestUrl === undefined) {
            break
        }
        const oldest = cache.get(oldestUrl)
        if (!oldest) {
            break
        }
        cache.delete(oldestUrl)
        cacheBytes -= oldest.size
    }
}

function cloneForResponse(data: unknown): unknown {
    // MapLibre runs TileJSON objects through `extend()`, which mutates them.
    // Return a shallow copy so the cached entry stays intact.
    if (isPlainObject(data) && !isImageBitmap(data)) {
        return { ...data }
    }
    return data
}

/**
 * Drop-in replacement for `omProtocol` that caches resolved TileJSON metadata
 * and rendered raster tiles in memory, keyed by request URL.
 */
export const cachedOmProtocol = (
    params: RequestParameters,
    abortController: AbortController,
): Promise<GetResourceResponse<any>> => {
    const url = params.url

    const hit = cache.get(url)
    if (hit) {
        // Move to the end so recently used entries survive eviction longest.
        cache.delete(url)
        cache.set(url, hit)
        return Promise.resolve({ data: cloneForResponse(hit.data) })
    }

    return omProtocol(params, abortController).then((response) => {
        if (response && response.data != null) {
            store(url, response.data)
        }
        return response
    })
}

export function clearWeatherMapCache(): void {
    cache.clear()
    cacheBytes = 0
}
