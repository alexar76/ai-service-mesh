import type { MeshStats } from '../lib/api';
import { useLocale } from '../i18n/LocaleContext';

const cards: { key: keyof MeshStats; labelKey: string; format?: (v: number) => string }[] = [
  { key: 'agents_verified', labelKey: 'stats_agents' },
  { key: 'tasks_24h', labelKey: 'stats_tasks' },
  { key: 'mesh_hops_24h', labelKey: 'stats_hops' },
  {
    key: 'success_rate_24h',
    labelKey: 'stats_success',
    format: (v) => `${(v * 100).toFixed(1)}%`,
  },
  {
    key: 'volume_usd_24h',
    labelKey: 'stats_volume',
    format: (v) => `$${v.toFixed(2)}`,
  },
];

export function StatsBar({ stats }: { stats: MeshStats }) {
  const { t } = useLocale();
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {cards.map(({ key, labelKey, format }) => (
        <div
          key={key}
          className="rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.06] to-transparent p-4"
        >
          <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">{t(labelKey)}</p>
          <p className="font-display text-2xl font-bold text-white tabular-nums">
            {format ? format(stats[key] as number) : String(stats[key])}
          </p>
        </div>
      ))}
    </div>
  );
}
