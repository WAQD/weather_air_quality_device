/**
 * @capacitor/background-runner task file.
 *
 * Runs in a V8 isolate — no window, no DOM, no Vue, no shared cookies.
 * Built by Vite as a self-contained IIFE into public/background-runner.js.
 *
 * Globals provided by the Background Runner runtime:
 *   CapacitorGeolocation, CapacitorPreferences, fetch, setTimeout, console
 *
 * The task is triggered by WeatherWidgetProvider.java on phone unlock when
 * GPS widget mode is active (via BackgroundRunner.dispatchEvent from Java /
 * or directly scheduled).
 */

import { formatWidgetPayload } from '../utils/widgetDataFormatter'

// ---- Ambient type declarations for the background runner globals ----

declare function addEventListener(
  event: string,
  callback: (resolve: () => void, reject: (reason?: unknown) => void, args: Record<string, unknown>) => void,
): void

declare const CapacitorGeolocation: {
  getCurrentPosition(opts: {
    enableHighAccuracy: boolean
    timeout: number
    maximumAge: number
  }): Promise<{ coords: { latitude: number; longitude: number } }>
}

declare const CapacitorPreferences: {
  get(opts: { key: string }): Promise<{ value: string | null }>
  set(opts: { key: string; value: string }): Promise<void>
}

// ---- Task registration ----

addEventListener('gpsWeatherRefresh', async (resolve, reject) => {
  try {
    // Read runtime config stored by the main app on first launch / login.
    const [baseUrlResult, styleResult, localeResult] = await Promise.all([
      CapacitorPreferences.get({ key: 'waqd.background.apiBaseUrl' }),
      CapacitorPreferences.get({ key: 'waqd.website.widgetStyle' }),
      CapacitorPreferences.get({ key: 'waqd.website.locale' }),
    ])

    const baseUrl = baseUrlResult.value ?? 'https://waqd.de'
    const widgetStyle = styleResult.value ?? 'simple'
    const locale = localeResult.value ?? 'en'

    // Acquire current GPS position.
    const position = await CapacitorGeolocation.getCurrentPosition({
      enableHighAccuracy: false,
      timeout: 10000,
      maximumAge: 60000,
    })
    const { latitude, longitude } = position.coords

    const params = new URLSearchParams({
      latitude: latitude.toString(),
      longitude: longitude.toString(),
      name: 'Selected location', // Triggers backend reverse geocoding
    })

    // Fetch weather from the backend.
    // NOTE: Background runner fetch does not share WebView cookies.
    // TODO: Replace with a dedicated widget token endpoint once the backend
    //       exposes /api/widget/weather that accepts a stored widget token.
    const response = await fetch(`${baseUrl}/api/user/weather/preview?${params.toString()}`)
    if (!response.ok) throw new Error(`Weather API returned ${response.status}`)

    const data = await response.json()

    // Use the shared formatter (bundled into this IIFE by Vite).
    const payload = formatWidgetPayload(
      data.current_weather,
      data.forecast ?? [],
      data.location,
      widgetStyle,
      locale,
      // No i18n available in the runner — condition shown as raw string.
    )

    // Persist to CapacitorStorage; WeatherWidgetProvider.java reads this key.
    await CapacitorPreferences.set({
      key: 'widget_weather_data',
      value: JSON.stringify(payload),
    })

    resolve()
  } catch (err) {
    console.error('[background-runner] gpsWeatherRefresh failed:', err)
    reject(err)
  }
})
