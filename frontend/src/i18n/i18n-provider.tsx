"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { messages, type Locale, type MessageKey } from "./messages";

type TranslationValues = Record<string, string | number>;

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, values?: TranslationValues) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);
const STORAGE_KEY = "ai-polyphite-locale";
const LOCALE_EVENT = "ai-polyphite-locale-change";

export function I18nProvider({ children }: Readonly<{ children: ReactNode }>) {
  const locale = useSyncExternalStore<Locale>(
    subscribeToLocale,
    getStoredLocale,
    (): Locale => "es-ES",
  );

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((nextLocale: Locale) => {
    window.localStorage.setItem(STORAGE_KEY, nextLocale);
    document.documentElement.lang = nextLocale;
    window.dispatchEvent(new Event(LOCALE_EVENT));
  }, []);

  const t = useCallback(
    (key: MessageKey, values: TranslationValues = {}) => {
      let text: string = messages[locale][key];
      for (const [name, value] of Object.entries(values)) {
        text = text.replaceAll(`{${name}}`, String(value));
      }
      return text;
    },
    [locale],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

function subscribeToLocale(onStoreChange: () => void): () => void {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(LOCALE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(LOCALE_EVENT, onStoreChange);
  };
}

function getStoredLocale(): Locale {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "en-US" ? "en-US" : "es-ES";
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (context === null) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
}
