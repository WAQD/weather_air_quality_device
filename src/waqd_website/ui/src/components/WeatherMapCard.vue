<template>
  <div v-if="currentLocation" class="relative card bg-base-100 shadow-xl overflow-hidden w-full"
    :aria-busy="isLoadingWeather">
    <div class="card-body p-0">
      <div class="flex flex-wrap items-center justify-between gap-2 px-3 pt-3">
        <div class="join">
          <button v-for="option in layerOptions" :key="option.id" type="button"
            class="btn btn-sm join-item"
            :class="activeLayer === option.id ? 'btn-primary' : 'btn-ghost'"
            @click="setActiveLayer(option.id)">
            {{ option.label }}
          </button>
        </div>
      </div>

      <div v-if="activeLayer !== 'none'" class="px-3 pt-2">
        <div>
          <input type="range" :min="minTimeOffset" :max="maxTimeOffset" step="1"
            v-model.number="timeOffset" class="range range-xs w-full" aria-label="Forecast hour" />
          <div class="relative h-4 text-[11px] leading-none opacity-70">
            <span v-for="(tick, i) in sliderTicks" :key="tick.text"
              class="absolute top-0 whitespace-nowrap" :class="{ 'hidden sm:inline': i === 0 }"
              :style="tickLabelStyle(tick, i, sliderTicks.length)">
              {{ tick.text }}
            </span>
          </div>
        </div>
        <div class="flex flex-col gap-1.5 px-1 pt-1 sm:flex-row sm:items-center sm:gap-2">
          <button type="button" class="link link-hover text-sm opacity-80"
            :disabled="timeOffset === 0" @click="timeOffset = 0">Now</button>
          <div class="flex items-center gap-2">
            <button type="button" class="btn btn-sm btn-outline btn-circle"
              :disabled="timeOffset <= minTimeOffset" @click="stepTime(-1)"
              aria-label="One hour earlier">−</button>
            <button type="button" class="btn btn-sm btn-primary btn-circle shrink-0"
              @click="togglePlayback" aria-label="Play animation">
              <span v-if="isPreloading || isLoadingFrame"
                class="loading loading-spinner loading-xs"></span>
              <svg v-else-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" class="h-3 w-3">
                <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="currentColor" class="h-3 w-3">
                <path d="M8 5v14l11-7z" />
              </svg>
            </button>
            <button type="button" class="btn btn-sm btn-outline btn-circle"
              :disabled="timeOffset >= maxTimeOffset" @click="stepTime(1)"
              aria-label="One hour later">+</button>
            <select v-model.number="playbackLength" class="select select-sm select-bordered"
              aria-label="Playback length">
              <option v-for="option in playbackOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
          <span class="whitespace-nowrap text-sm opacity-80 sm:ml-auto">{{ timeLabel
          }}</span>
        </div>
      </div>

      <div class="relative">
        <div ref="mapContainer" class="h-[400px] w-full"></div>
        <div v-if="isLoading"
          class="absolute inset-0 flex items-center justify-center bg-base-200/60">
          <span class="loading loading-spinner loading-lg"></span>
        </div>
        <div v-if="isLoadingWeather" class="absolute inset-0 z-10">
          <div class="skeleton h-full w-full"></div>
        </div>
      </div>

      <div v-if="activeLegend" class="px-4 pt-2">
        <div class="h-2.5 w-full rounded-sm bg-base-200"
          :style="{ backgroundImage: activeLegend.gradient }"></div>
        <div class="relative mt-1 h-4 text-[10px] leading-none opacity-80">
          <span v-for="(label, i) in activeLegend.labels" :key="i"
            class="absolute top-0 whitespace-nowrap"
            :style="legendLabelStyle(label, i, activeLegend.labels.length)">
            {{ label.text }}
          </span>
        </div>
      </div>

      <div class="text-xs p-2 text-center opacity-70 flex flex-wrap justify-center gap-x-3 gap-y-1">
        <span>Weather © <a href="https://open-meteo.com" target="_blank"
            class="hover:underline">Open-Meteo</a></span>
        <span>Map © <a href="https://www.openstreetmap.org/copyright" target="_blank"
            class="hover:underline">OpenStreetMap</a> contributors</span>
        <a :href="osmLinkUrl" target="_blank" class="hover:underline">
          View Larger Map
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type {
  Map as MapLibreMap,
  Marker as MapLibreMarker,
  RasterTileSource,
  StyleSpecification,
} from 'maplibre-gl'
import type { RenderableColorScale } from '@openmeteo/weather-map-layer'
import { useWebsiteWeather } from '../composables/useWebsiteWeather'

type MapLibreGL = typeof import('maplibre-gl')
type LayerId = 'temperature' | 'precipitation' | 'none'
type Rgba = [number, number, number, number]

interface LegendLabel {
  text: string
  pct: number
}

interface LegendScale {
  gradient: string
  labels: LegendLabel[]
}

function rgbaToCss([r, g, b, a]: Rgba): string {
  return `rgba(${r}, ${g}, ${b}, ${a})`
}

function niceStep(range: number, targetTicks = 5): number {
  const target = range / targetTicks
  const magnitude = 10 ** Math.floor(Math.log10(target))
  const normalized = target / magnitude
  const step = normalized < 1.5 ? 1 : normalized < 3.5 ? 2 : normalized < 7.5 ? 5 : 10
  return step * magnitude
}

function formatLegendValue(value: number, step: number): string {
  if (step >= 1) {
    return Math.round(value).toString()
  }
  if (step >= 0.1) {
    return (Math.round(value * 10) / 10).toString()
  }
  return (Math.round(value * 100) / 100).toString()
}

function buildLegendScale(scale: RenderableColorScale): LegendScale {
  let min: number
  let max: number
  let unit: string
  let stops: { value: number; color: string }[]

  if (scale.type === 'breakpoint') {
    unit = scale.unit
    const breakpoints = scale.breakpoints
    min = breakpoints[0]!
    max = breakpoints[breakpoints.length - 1]!
    stops = breakpoints.map((bp, i) => ({ value: bp, color: rgbaToCss(scale.colors[i]!) }))
  } else {
    unit = scale.unit
    min = scale.min
    max = scale.max
    const colors = scale.colors
    stops = colors.map((color, i) => ({
      value: min + ((max - min) * i) / (colors.length - 1),
      color: rgbaToCss(color),
    }))
  }

  const range = max - min
  if (range <= 0) {
    return { gradient: 'none', labels: [] }
  }

  const gradient = `linear-gradient(to right, ${stops
    .map((stop) => `${stop.color} ${(((stop.value - min) / range) * 100).toFixed(2)}%`)
    .join(', ')})`

  const step = niceStep(range)
  const start = Math.ceil(min / step) * step
  const values: number[] = []
  if (start - min > step * 0.5) {
    values.push(min)
  }
  for (let value = start; value < max; value += step) {
    values.push(value)
  }
  const last = values[values.length - 1]
  if (last === undefined || max - last > step * 0.5) {
    values.push(max)
  }

  const unitSuffix = unit.startsWith('°') ? unit : ` ${unit}`
  const labels: LegendLabel[] = values.map((value) => ({
    text: `${formatLegendValue(value, step)}${unitSuffix}`,
    pct: Math.max(0, Math.min(100, ((value - min) / range) * 100)),
  }))

  return { gradient, labels }
}

function legendLabelStyle(label: LegendLabel, index: number, total: number): Record<string, string> {
  if (index === 0) {
    return { left: '0%' }
  }
  if (index === total - 1) {
    return { right: '0%' }
  }
  return { left: `${label.pct}%`, transform: 'translateX(-50%)' }
}

const tickLabelStyle = legendLabelStyle

const DATA_BASE_URL = 'https://openmeteo-data-spatial.b-cdn.net/dwd_icon/latest.json'

// Inline OSM raster base map. Open-Meteo's hosted style uses tiles from
// tiles.open-meteo.com, which does not send CORS headers for third-party
// production origins, so we use OSM tiles (CORS `*`) instead.
const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    { id: 'osm', type: 'raster', source: 'osm' },
  ],
}

const { currentLocation, isLoadingWeather } = useWebsiteWeather()

const mapContainer = ref<HTMLElement | null>(null)
const activeLayer = ref<LayerId>('temperature')
const isLoading = ref(false)
const timeOffset = ref(0)
const minTimeOffset = -6
const maxTimeOffset = 72

// Slider tick labels: -6h, Now, then 12h increments up to +72h.
const sliderTicks: LegendLabel[] = [-6, 0, 12, 24, 36, 48, 60, 72].map((offset) => ({
  text: offset === 0 ? 'Now' : `${offset > 0 ? '+' : ''}${offset}h`,
  pct: ((offset - minTimeOffset) / (maxTimeOffset - minTimeOffset)) * 100,
}))
const playbackLength = ref(12)
const playbackOptions: { value: number; label: string }[] = [
  { value: 12, label: '+12h' },
  { value: 24, label: '+24h' },
  { value: 36, label: '+36h' },
  { value: 48, label: '+48h' },
  { value: 60, label: '+60h' },
  { value: 72, label: '+72h' },
]
const isPlaying = ref(false)
const isPreloading = ref(false)
const isLoadingFrame = ref(false)
let preloadCancelled = false
const colorScales = ref<{ temperature: LegendScale | null; precipitation: LegendScale | null }>({
  temperature: null,
  precipitation: null,
})

const activeLegend = computed<LegendScale | null>(() => {
  if (activeLayer.value === 'temperature') {
    return colorScales.value.temperature
  }
  if (activeLayer.value === 'precipitation') {
    return colorScales.value.precipitation
  }
  return null
})

const timeLabel = computed(() => {
  const utcHour = Math.floor(Date.now() / 3_600_000)
  const frame = new Date((utcHour + timeOffset.value) * 3_600_000)
  return frame.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const layerOptions: { id: LayerId; label: string }[] = [
  { id: 'temperature', label: 'Temperature' },
  { id: 'precipitation', label: 'Precipitation' },
  { id: 'none', label: 'Base map' },
]

let map: MapLibreMap | null = null
let marker: MapLibreMarker | null = null
let initPromise: Promise<void> | null = null

const osmLinkUrl = computed(() => {
  if (!currentLocation.value) {
    return ''
  }

  const lat = currentLocation.value.latitude
  const lon = currentLocation.value.longitude
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=8/${lat}/${lon}`
})

function timeStepFor(offset: number): string {
  if (offset === 0) {
    return 'current_time'
  }
  const sign = offset > 0 ? '+' : '-'
  return `current_time_${sign}${Math.abs(offset)}H`
}

function layerSourceUrl(variable: string, offset: number): string {
  return `om://${DATA_BASE_URL}?time_step=${timeStepFor(offset)}&variable=${variable}&tile_size=256`
}

function stepTime(delta: number): void {
  timeOffset.value = Math.max(minTimeOffset, Math.min(maxTimeOffset, timeOffset.value + delta))
}

const PLAY_INTERVAL_MS = 350
const FADE_MS = 300
const FRAME_LOAD_TIMEOUT_MS = 1500
const WEATHER_OPACITY = 0.75

type WeatherVariable = 'temperature' | 'precipitation'

const OM_VARIABLE: Record<WeatherVariable, string> = {
  temperature: 'temperature_2m',
  precipitation: 'precipitation',
}

interface FrameBuffer {
  offset: number | null
  ready: Promise<void> | null
}

// Double buffering: each weather variable owns two raster sources/layers.
// The next frame loads into the hidden buffer and is then cross-faded in,
// so the visible frame is never cleared while new tiles load (no flicker).
const buffers: Record<WeatherVariable, { active: 0 | 1; frames: [FrameBuffer, FrameBuffer] }> = {
  temperature: { active: 0, frames: [{ offset: null, ready: null }, { offset: null, ready: null }] },
  precipitation: { active: 0, frames: [{ offset: null, ready: null }, { offset: null, ready: null }] },
}

function applyTimeOffset(offset: number = timeOffset.value): void {
  if (!map) {
    return
  }

  for (const variable of ['temperature', 'precipitation'] as const) {
    const state = buffers[variable]
    // Only touch the active variable; the other one loads on demand when
    // its layer is selected.
    if (activeLayer.value === variable && state.frames[state.active].offset !== offset) {
      void requestFrame(variable, offset)
    }
  }
}

function bufferSourceId(variable: WeatherVariable, index: number): string {
  return `weather-${variable}-${index}`
}

function setBufferOpacity(variable: WeatherVariable, index: number, opacity: number): void {
  const layerId = bufferSourceId(variable, index)
  if (!map || !map.getLayer(layerId)) {
    return
  }
  map.setPaintProperty(layerId, 'raster-opacity', opacity)
}

function targetOpacity(variable: WeatherVariable): number {
  return activeLayer.value === variable ? WEATHER_OPACITY : 0
}

function loadBuffer(variable: WeatherVariable, index: number, offset: number): Promise<void> {
  const layerId = bufferSourceId(variable, index)
  const source = map?.getSource(layerId) as RasterTileSource | undefined
  if (!map || !source) {
    return Promise.resolve()
  }

  // Sources start with visibility 'none' so unused buffers never fetch tiles.
  map.setLayoutProperty(layerId, 'visibility', 'visible')
  try {
    source.setUrl(layerSourceUrl(OM_VARIABLE[variable], offset))
  } catch {
    return Promise.resolve()
  }
  return waitForMapIdle(FRAME_LOAD_TIMEOUT_MS)
}

/**
 * Cross-fade the given frame into view. If the hidden buffer already holds the
 * frame (prefetched), only the fade runs. No-op when the frame is visible.
 */
async function showFrame(variable: WeatherVariable, offset: number): Promise<void> {
  const state = buffers[variable]
  if (state.frames[state.active].offset === offset) {
    setBufferOpacity(variable, state.active, targetOpacity(variable))
    return
  }

  const backIndex = (1 - state.active) as 0 | 1
  const back = state.frames[backIndex]
  if (back.offset !== offset) {
    back.offset = offset
    back.ready = loadBuffer(variable, backIndex, offset)
  }
  await back.ready
  if (!map) {
    return
  }

  setBufferOpacity(variable, backIndex, targetOpacity(variable))
  setBufferOpacity(variable, state.active, 0)
  state.active = backIndex
}

/** Load a frame into the hidden buffer in the background (fire and forget). */
function prefetchFrame(variable: WeatherVariable, offset: number): void {
  if (offset < minTimeOffset || offset > maxTimeOffset) {
    return
  }
  const state = buffers[variable]
  const hiddenIndex = (1 - state.active) as 0 | 1
  const hidden = state.frames[hiddenIndex]
  if (hidden.offset === offset) {
    return
  }
  hidden.offset = offset
  hidden.ready = loadBuffer(variable, hiddenIndex, offset)
}

// Latest-wins frame requests keep slider scrubbing responsive: intermediate
// offsets are skipped instead of queued behind slow tile loads.
let scrubRequest: { variable: WeatherVariable; offset: number; resolve: () => void } | null = null
let scrubWorkerRunning = false

function requestFrame(variable: WeatherVariable, offset: number): Promise<void> {
  if (!map) {
    return Promise.resolve()
  }
  return new Promise((resolve) => {
    scrubRequest?.resolve()
    scrubRequest = { variable, offset, resolve }
    if (!scrubWorkerRunning) {
      void scrubWorker()
    }
  })
}

async function scrubWorker(): Promise<void> {
  scrubWorkerRunning = true
  while (scrubRequest) {
    const { variable, offset, resolve } = scrubRequest
    scrubRequest = null
    await showFrame(variable, offset)
    resolve()
  }
  scrubWorkerRunning = false
}

function stopPlayback(): void {
  isPlaying.value = false
}

function togglePlayback(): void {
  if (isPreloading.value) {
    preloadCancelled = true
    return
  }

  if (isPlaying.value) {
    stopPlayback()
    return
  }

  void startPlayback()
}

async function startPlayback(): Promise<void> {
  if (!map || isPlaying.value || activeLayer.value === 'none') {
    return
  }
  const variable = activeLayer.value

  if (timeOffset.value >= maxTimeOffset) {
    timeOffset.value = 0
  }

  const end = Math.min(maxTimeOffset, timeOffset.value + playbackLength.value)

  // Prime the pipeline: show the current frame and start loading the next
  // one before the loop begins.
  isPreloading.value = true
  preloadCancelled = false
  await showFrame(variable, timeOffset.value)
  prefetchFrame(variable, timeOffset.value + 1)
  isPreloading.value = false

  if (preloadCancelled || !map) {
    return
  }

  isPlaying.value = true
  while (isPlaying.value && timeOffset.value < end) {
    const next = timeOffset.value + 1
    const started = performance.now()
    isLoadingFrame.value = true
    await showFrame(variable, next)
    isLoadingFrame.value = false
    if (!isPlaying.value) {
      break
    }
    timeOffset.value = next
    // The buffer that just faded out is free: start loading the frame
    // after next into it while the current one is displayed.
    prefetchFrame(variable, next + 1)
    const elapsed = performance.now() - started
    await new Promise((resolve) =>
      window.setTimeout(resolve, Math.max(0, PLAY_INTERVAL_MS - elapsed)),
    )
  }
  stopPlayback()
}

function waitForMapIdle(timeoutMs: number): Promise<void> {
  const instance = map
  if (!instance) {
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    let settled = false
    const finish = () => {
      if (settled) {
        return
      }
      settled = true
      instance.off('idle', onIdle)
      window.clearTimeout(timer)
      resolve()
    }
    const onIdle = () => finish()
    instance.once('idle', onIdle)
    const timer = window.setTimeout(finish, timeoutMs)
  })
}

function applyActiveLayer(): void {
  if (!map) {
    return
  }

  for (const variable of ['temperature', 'precipitation'] as const) {
    const state = buffers[variable]
    setBufferOpacity(variable, state.active, targetOpacity(variable))
    setBufferOpacity(variable, 1 - state.active, 0)
  }
}

function setActiveLayer(layer: LayerId): void {
  if (isPlaying.value || isPreloading.value) {
    preloadCancelled = true
    stopPlayback()
  }
  activeLayer.value = layer
  applyActiveLayer()
  if (layer !== 'none') {
    // Only the active variable is loaded; fetch the current frame for a
    // freshly selected layer on demand.
    void requestFrame(layer, timeOffset.value)
  }
}

function recenter(): void {
  if (!map || !currentLocation.value) {
    return
  }

  const { latitude, longitude } = currentLocation.value
  map.flyTo({ center: [longitude, latitude], zoom: 8 })
  marker?.setLngLat([longitude, latitude])
}

async function initMap(): Promise<void> {
  if (map || !mapContainer.value || !currentLocation.value) {
    return
  }

  if (initPromise) {
    return initPromise
  }

  const location = currentLocation.value

  initPromise = (async () => {
    isLoading.value = true
    try {
      const [maplibreModule, , mapLayerModule, mapCacheModule] = await Promise.all([
        import('maplibre-gl'),
        import('maplibre-gl/dist/maplibre-gl.css'),
        import('@openmeteo/weather-map-layer'),
        import('../utils/weatherMapCache'),
      ])
      const maplibregl = (maplibreModule as unknown as { default: MapLibreGL }).default
      const { getColorScale } = mapLayerModule
      const { cachedOmProtocol } = mapCacheModule

      maplibregl.addProtocol('om', cachedOmProtocol)

      colorScales.value.temperature = buildLegendScale(getColorScale('temperature_2m', false))
      colorScales.value.precipitation = buildLegendScale(getColorScale('precipitation', false))

      const { latitude, longitude } = location
      const instance = new maplibregl.Map({
        container: mapContainer.value as HTMLElement,
        style: BASE_STYLE,
        center: [longitude, latitude],
        zoom: 8,
        attributionControl: false,
      })

      map = instance
      marker = new maplibregl.Marker().setLngLat([longitude, latitude]).addTo(instance)

      instance.addControl(
        new maplibregl.NavigationControl({ showCompass: false }),
        'top-right',
      )

      instance.on('load', () => {
        // Two sources/layers per variable enable double buffering:
        // frames load into a hidden buffer and cross-fade in when ready.
        // Sources start with visibility 'none' so no tiles are fetched
        // until a buffer is actually used.
        for (const variable of ['temperature', 'precipitation'] as const) {
          for (const index of [0, 1] as const) {
            const id = bufferSourceId(variable, index)
            instance.addSource(id, {
              type: 'raster',
              url: layerSourceUrl(OM_VARIABLE[variable], timeOffset.value),
              tileSize: 256,
              maxzoom: 12,
            })
            instance.addLayer({
              id,
              type: 'raster',
              source: id,
              layout: { visibility: 'none' },
              paint: {
                'raster-opacity': 0,
                'raster-opacity-transition': { duration: FADE_MS, delay: 0 },
              },
            })
          }
        }

        applyActiveLayer()
        applyTimeOffset()
      })
    } catch (error) {
      console.error('Failed to initialize weather map', error)
    } finally {
      isLoading.value = false
    }
  })()

  await initPromise
  initPromise = null
}

function destroyMap(): void {
  if (map) {
    map.remove()
    map = null
    marker = null
  }
  for (const variable of ['temperature', 'precipitation'] as const) {
    buffers[variable] = {
      active: 0,
      frames: [
        { offset: null, ready: null },
        { offset: null, ready: null },
      ],
    }
  }
  initPromise = null
}

onMounted(() => {
  if (currentLocation.value) {
    void initMap()
  }
})

watch(currentLocation, async (location) => {
  if (!location) {
    destroyMap()
    return
  }

  if (!map) {
    await nextTick()
    await initMap()
  } else {
    recenter()
  }
})

watch(timeOffset, () => {
  applyTimeOffset()
})

onBeforeUnmount(() => {
  stopPlayback()
  destroyMap()
})
</script>
