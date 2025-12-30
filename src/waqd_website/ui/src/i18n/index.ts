import { createI18n } from 'vue-i18n'

export type MessageSchema = Record<string, string>

export type AvailableLocale = 'en' | 'de' | 'hu'

// Track which locales have been loaded
const loadedLocales = new Set<AvailableLocale>()

// Create i18n instance with only English loaded initially
const i18n = createI18n<[MessageSchema], AvailableLocale>({
  locale: 'en', // default locale
  fallbackLocale: 'en',
  messages: {
    en: {},
    de: {},
    hu: {},
  },
  legacy: false, // Use Composition API mode
  globalInjection: true, // Inject $t globally
})

/**
 * Dynamically load a locale's messages
 */
async function loadLocaleMessages(locale: AvailableLocale): Promise<void> {
  // If already loaded, skip
  if (loadedLocales.has(locale)) {
    return
  }

  try {
    // Fetch the locale JSON file from static assets
    const response = await fetch(`/static/locales/${locale}.json`)
    if (!response.ok) {
      throw new Error(`Failed to fetch locale ${locale}: ${response.statusText}`)
    }
    const messages = await response.json()
    
    // Set the locale messages
    i18n.global.setLocaleMessage(locale, messages)
    
    // Mark as loaded
    loadedLocales.add(locale)
  } catch (error) {
    console.error(`Failed to load locale ${locale}:`, error)
    throw error
  }
}

/**
 * Change the current locale (with lazy loading)
 */
export async function setLocale(locale: AvailableLocale): Promise<void> {
  // Load the locale if not already loaded
  await loadLocaleMessages(locale)
  
  // @ts-ignore - locale.value type issue with vue-i18n
  i18n.global.locale.value = locale
  
  // Store preference in localStorage
  localStorage.setItem('waqd-locale', locale)
}

/**
 * Get the stored locale preference or default to 'en'
 */
export function getStoredLocale(): AvailableLocale {
  const stored = localStorage.getItem('waqd-locale')
  if (stored === 'de' || stored === 'hu') {
    return stored
  }
  return 'en'
}

/**
 * Initialize i18n with the stored locale
 */
export async function initI18n(): Promise<void> {
  const storedLocale = getStoredLocale()
  await loadLocaleMessages(storedLocale)
  // @ts-ignore
  i18n.global.locale.value = storedLocale
}

export default i18n
