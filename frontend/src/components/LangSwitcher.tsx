import { SUPPORTED_UI_LOCALES } from '../i18n/strings';
import { useLocale } from '../i18n/LocaleContext';

export function LangSwitcher() {
  const { lang, setLang } = useLocale();
  return (
    <span
      className="inline-flex gap-0.5 rounded-full border border-teal-500/25 bg-teal-500/5 p-0.5"
      aria-label="Language"
    >
      {SUPPORTED_UI_LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code)}
          className={`rounded-full px-2 py-1 text-[11px] font-semibold tracking-wider uppercase transition ${
            lang === code
              ? 'bg-teal-500/25 text-amber-200'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          {code}
        </button>
      ))}
    </span>
  );
}
