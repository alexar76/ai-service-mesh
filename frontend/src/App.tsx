import { useCallback, useEffect, useState } from 'react';
import { meshApi, type ActivityEvent, type Agent, type MeshStats, type Task } from './lib/api';
import { ActivityFeed } from './components/ActivityFeed';
import { AgentGrid } from './components/AgentGrid';
import { LangSwitcher } from './components/LangSwitcher';
import { MeshLiveScene } from './components/MeshLiveScene';
import { StatsBar } from './components/StatsBar';
import { useLocale } from './i18n/LocaleContext';

const SLOW_POLL_MS = 12_000;

export default function App() {
  const { t } = useLocale();
  const [stats, setStats] = useState<MeshStats | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [focusTaskId, setFocusTaskId] = useState<string | null>(null);

  const refreshCore = useCallback(async () => {
    try {
      const [s, a, tsk] = await Promise.all([
        meshApi.stats(),
        meshApi.agents(),
        meshApi.tasks(24),
      ]);
      setStats(s);
      setAgents(a);
      setTasks(tsk);
      setError(null);
      setFocusTaskId((cur) => cur ?? tsk[0]?.id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'API unreachable');
    }
  }, []);

  const refreshActivity = useCallback(async () => {
    try {
      const ev = await meshApi.activity(100);
      setActivity(ev);
    } catch {
      /* SSE is primary */
    }
  }, []);

  useEffect(() => {
    void refreshCore();
    void refreshActivity();
    const id = setInterval(() => void refreshCore(), SLOW_POLL_MS);
    return () => clearInterval(id);
  }, [refreshCore, refreshActivity]);

  useEffect(() => {
    let es: EventSource | null = null;
    let closed = false;
    let retry: number | undefined;

    const connect = () => {
      if (closed) return;
      es = new EventSource(meshApi.activityStreamUrl());
      es.onopen = () => setLive(true);
      es.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data) as ActivityEvent;
          setActivity((prev) => {
            if (prev.some((e) => e.id === event.id)) return prev;
            return [...prev, event].slice(-120);
          });
          if (event.task_id) setFocusTaskId(event.task_id);
        } catch {
          /* ignore */
        }
      };
      es.onerror = () => {
        setLive(false);
        es?.close();
        retry = window.setTimeout(connect, 4000);
      };
    };

    connect();
    return () => {
      closed = true;
      if (retry) window.clearTimeout(retry);
      es?.close();
    };
  }, []);

  return (
    <div className="mesh-grid min-h-screen">
      <header className="border-b border-white/10 bg-black/50 backdrop-blur-xl sticky top-0 z-20">
        <div className="mx-auto max-w-7xl px-4 py-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-teal-400/90">
              {t('brand_sub')}
            </p>
            <h1 className="font-display text-2xl md:text-3xl font-bold text-white tracking-tight">
              {t('title')}
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">{t('subtitle')}</p>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400 flex-wrap">
            <LangSwitcher />
            <span
              className={`live-dot inline-block h-2 w-2 rounded-full ${live ? 'bg-emerald-400' : 'bg-amber-400'}`}
            />
            {live ? t('sse_ok') : t('sse_wait')}
            <a
              className="text-teal-300/90 hover:text-teal-200 underline-offset-2 hover:underline"
              href="https://alexar76.github.io/ai-service-mesh/"
              target="_blank"
              rel="noreferrer"
            >
              {t('landing')}
            </a>
          </div>
        </div>
      </header>

      <main className="space-y-0">
        {error && (
          <div className="mx-auto max-w-7xl px-4 pt-4">
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              {t('api_fail')}: <code className="font-mono text-cyan-300">{error}</code>
            </div>
          </div>
        )}

        {stats && (
          <div className="mx-auto max-w-7xl px-4 pt-6 pb-4">
            <StatsBar stats={stats} />
          </div>
        )}

        <MeshLiveScene
          agents={agents}
          tasks={tasks}
          activity={activity}
          focusTaskId={focusTaskId}
          onSelectTask={setFocusTaskId}
        />

        <div className="mx-auto max-w-7xl px-4 py-8">
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <ActivityFeed events={activity} />
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <h2 className="font-display text-lg font-semibold text-white mb-4">{t('recent_tasks')}</h2>
                <ul className="space-y-3">
                  {tasks.length === 0 && (
                    <li className="text-sm text-slate-500">{t('no_tasks')}</li>
                  )}
                  {tasks.map((task) => (
                    <li key={task.id}>
                      <button
                        type="button"
                        onClick={() => setFocusTaskId(task.id)}
                        className={`w-full text-left rounded-xl border px-4 py-3 text-sm transition ${
                          focusTaskId === task.id
                            ? 'border-teal-400/40 bg-teal-500/10'
                            : 'border-white/5 bg-black/30 hover:border-white/15'
                        }`}
                      >
                        <div className="flex flex-wrap justify-between gap-2 mb-1">
                          <span className="font-mono text-xs text-cyan-300/80">{task.id}</span>
                          <span
                            className={`text-xs font-medium uppercase ${
                              task.status === 'completed'
                                ? 'text-emerald-400'
                                : task.status === 'failed'
                                  ? 'text-rose-400'
                                  : 'text-amber-300'
                            }`}
                          >
                            {task.status}
                          </span>
                        </div>
                        <p className="text-slate-300 line-clamp-2">{task.intent}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {task.hops.length} {t('hops')} · ${task.total_spent_usd.toFixed(2)} {t('spent')}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="space-y-6">
              <AgentGrid agents={agents} />
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-white/5 py-6 text-center text-xs text-slate-600">
        AI Service Mesh ·{' '}
        <a className="text-slate-500 hover:text-teal-300" href="https://service-mesh.modelmarket.dev/v1/stats">
          {t('foot_stats')}
        </a>
      </footer>
    </div>
  );
}
