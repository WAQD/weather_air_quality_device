import { createI18n } from 'vue-i18n'

export type MessageSchema = {
  [key: string]: string
}

export type AvailableLocale = 'en' | 'de' | 'hu'

// Create i18n instance with initial empty messages
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
 * Load translations from the backend ui_dict.json
 * New format: { "key": { "en": "value", "de": "wert" } }
 */
export async function loadTranslations() {
  try {
    const response = await fetch('/static/base/ui_dict.json')
    if (!response.ok) {
      throw new Error(`Failed to load translations: ${response.statusText}`)
    }
    
    const translations = await response.json()
    
    // Convert from key-first to language-first structure for vue-i18n
    const messages: Record<string, Record<string, string>> = {
      en: {},
      de: {},
      hu: {},
    }
    
    for (const [key, langObj] of Object.entries(translations)) {
      const langs = langObj as Record<string, string>
      for (const [lang, value] of Object.entries(langs)) {
        if (messages[lang]) {
          messages[lang][key] = value
        }
      }
    }
    
    // Set messages for each locale
    i18n.global.setLocaleMessage('en', messages.en || {})
    i18n.global.setLocaleMessage('de', messages.de || {})
    i18n.global.setLocaleMessage('hu', messages.hu || {})
    
    return true
  } catch (error) {
    console.error('Error loading translations:', error)
    return false
  }
}

/**
 * Change the current locale
 */
export function setLocale(locale: AvailableLocale) {
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

export default i18n
