import { computed } from 'vue'
import { useI18n as vueUseI18n } from 'vue-i18n'
import { setLocale as setI18nLocale, getStoredLocale, type AvailableLocale } from '../i18n'

/**
 * Composable for using translations in components
 * Provides the translation function and locale management
 */
export function useTranslation() {
  const { t, locale } = vueUseI18n()

  const currentLocale = computed(() => locale.value as AvailableLocale)

  const setLocale = (newLocale: AvailableLocale) => {
    setI18nLocale(newLocale)
  }

  return {
    t,
    locale: currentLocale,
    setLocale,
    getStoredLocale,
  }
}
