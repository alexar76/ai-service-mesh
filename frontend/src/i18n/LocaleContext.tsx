import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import {
  readStoredLocale,
  translate,
  writeStoredLocale,
  type UiLocale,
} from './strings';

type Ctx = {
  lang: UiLocale;
  setLang: (l: UiLocale) => void;
  t: (key: string) => string;
};

const LocaleContext = createContext<Ctx | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<UiLocale>(() => readStoredLocale());

  const setLang = useCallback((l: UiLocale) => {
    setLangState(l);
    writeStoredLocale(l);
    document.documentElement.lang = l;
  }, []);

  const t = useCallback((key: string) => translate(lang, key), [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error('useLocale outside LocaleProvider');
  return ctx;
}
