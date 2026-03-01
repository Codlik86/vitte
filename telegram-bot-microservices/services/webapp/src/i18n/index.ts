import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ru from "./locales/ru.json";
import en from "./locales/en.json";

function detectLanguage(): string {
  try {
    const tgLang = (window as any).Telegram?.WebApp?.initDataUnsafe?.user
      ?.language_code as string | undefined;
    if (tgLang === "ru") return "ru";
    if (tgLang === "en") return "en";
  } catch {
    // ignore
  }
  return "ru";
}

i18n.use(initReactI18next).init({
  resources: {
    ru: { translation: ru },
    en: { translation: en },
  },
  lng: detectLanguage(),
  fallbackLng: "ru",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
