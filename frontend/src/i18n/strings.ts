/** UI chrome for mesh dashboard — en/ru/es/fr/zh.
 * Terms follow docs/localization-glossary.md (product names stay Latin).
 */
export const SUPPORTED_UI_LOCALES = ['en', 'ru', 'es', 'fr', 'zh'] as const;
export type UiLocale = (typeof SUPPORTED_UI_LOCALES)[number];

export const LANG_STORAGE_KEY = 'ai-service-mesh-lang';

type Dict = Record<string, string>;

export const I18N: Record<UiLocale, Dict> = {
  en: {
    brand_sub: 'AI Service Mesh',
    title: 'Live activity',
    subtitle: 'Discover → verify → escrow → invoke → settle — real registry peers and task hops.',
    sse_ok: 'SSE connected',
    sse_wait: 'Reconnecting…',
    landing: 'Landing',
    api_fail: 'API read failed',
    live_mesh: 'Live mesh',
    topology: 'Topology',
    peers_one: 'verified peer',
    peers_many: 'verified peers',
    packets_hint: 'Packets replay real task hops and activity stream events.',
    focus_task: 'Focus task',
    activity: 'Activity stream',
    events: 'events',
    waiting: 'Waiting for mesh events…',
    recent_tasks: 'Recent tasks',
    no_tasks: 'No completed mesh tasks yet.',
    hops: 'hops',
    spent: 'spent',
    verified_agents: 'Verified agents',
    trust: 'trust',
    stats_agents: 'Verified agents',
    stats_tasks: 'Tasks (24h)',
    stats_hops: 'Mesh hops (24h)',
    stats_success: 'Success rate',
    stats_volume: 'Volume (24h)',
    hub: 'Mesh Core',
    hub_sub: 'zero-trust router',
    foot_stats: '/v1/stats',
  },
  ru: {
    brand_sub: 'AI Service Mesh',
    title: 'Живая активность',
    subtitle: 'Обнаружение → верификация → эскроу → вызов → расчёт — реальные пиры реестра и хопы задач.',
    sse_ok: 'SSE подключён',
    sse_wait: 'Переподключение…',
    landing: 'Лендинг',
    api_fail: 'Ошибка чтения API',
    live_mesh: 'Живой меш',
    topology: 'Топология',
    peers_one: 'верифицированный пир',
    peers_many: 'верифицированных пиров',
    packets_hint: 'Пакеты воспроизводят реальные хопы задач и события потока активности.',
    focus_task: 'Фокус задачи',
    activity: 'Поток активности',
    events: 'событий',
    waiting: 'Ждём события меша…',
    recent_tasks: 'Недавние задачи',
    no_tasks: 'Пока нет завершённых задач меша.',
    hops: 'хопов',
    spent: 'потрачено',
    verified_agents: 'Верифицированные агенты',
    trust: 'доверие',
    stats_agents: 'Верифицированные агенты',
    stats_tasks: 'Задачи (24ч)',
    stats_hops: 'Хопы меша (24ч)',
    stats_success: 'Успешность',
    stats_volume: 'Объём (24ч)',
    hub: 'Mesh Core',
    hub_sub: 'маршрутизатор нулевого доверия',
    foot_stats: '/v1/stats',
  },
  es: {
    brand_sub: 'AI Service Mesh',
    title: 'Actividad en vivo',
    subtitle: 'Descubrimiento → verificación → depósito en garantía → invocación → liquidación — peers reales y saltos (hops).',
    sse_ok: 'SSE conectado',
    sse_wait: 'Reconectando…',
    landing: 'Landing',
    api_fail: 'Fallo de lectura API',
    live_mesh: 'Malla en vivo',
    topology: 'Topología',
    peers_one: 'peer verificado',
    peers_many: 'peers verificados',
    packets_hint: 'Los paquetes reproducen saltos (hops) reales y el flujo de actividad.',
    focus_task: 'Tarea en foco',
    activity: 'Flujo de actividad',
    events: 'eventos',
    waiting: 'Esperando eventos de la malla…',
    recent_tasks: 'Tareas recientes',
    no_tasks: 'Aún no hay tareas completadas.',
    hops: 'saltos',
    spent: 'gastado',
    verified_agents: 'Agentes verificados',
    trust: 'confianza',
    stats_agents: 'Agentes verificados',
    stats_tasks: 'Tareas (24h)',
    stats_hops: 'Saltos mesh (24h)',
    stats_success: 'Tasa de éxito',
    stats_volume: 'Volumen (24h)',
    hub: 'Mesh Core',
    hub_sub: 'enrutador de confianza cero',
    foot_stats: '/v1/stats',
  },
  fr: {
    brand_sub: 'AI Service Mesh',
    title: 'Activité en direct',
    subtitle: 'Découverte → vérification → séquestre → invocation → règlement — pairs réels et sauts (hops).',
    sse_ok: 'SSE connecté',
    sse_wait: 'Reconnexion…',
    landing: 'Landing',
    api_fail: 'Échec de lecture API',
    live_mesh: 'Maillage live',
    topology: 'Topologie',
    peers_one: 'pair vérifié',
    peers_many: 'pairs vérifiés',
    packets_hint: 'Les paquets rejouent les sauts (hops) réels et le flux d’activité.',
    focus_task: 'Tâche focalisée',
    activity: 'Flux d’activité',
    events: 'événements',
    waiting: 'En attente d’événements du mesh…',
    recent_tasks: 'Tâches récentes',
    no_tasks: 'Pas encore de tâches terminées.',
    hops: 'sauts',
    spent: 'dépensé',
    verified_agents: 'Agents vérifiés',
    trust: 'confiance',
    stats_agents: 'Agents vérifiés',
    stats_tasks: 'Tâches (24h)',
    stats_hops: 'Sauts mesh (24h)',
    stats_success: 'Taux de succès',
    stats_volume: 'Volume (24h)',
    hub: 'Mesh Core',
    hub_sub: 'routeur confiance zéro',
    foot_stats: '/v1/stats',
  },
  zh: {
    brand_sub: 'AI Service Mesh',
    title: '实时活动',
    subtitle: '发现 → 验证 → 托管 → 调用 → 结算 — 真实注册表对等节点与任务跳（hop）。',
    sse_ok: 'SSE 已连接',
    sse_wait: '正在重连…',
    landing: '落地页',
    api_fail: 'API 读取失败',
    live_mesh: '实时网格',
    topology: '拓扑',
    peers_one: '个已验证对等节点',
    peers_many: '个已验证对等节点',
    packets_hint: '数据包回放真实任务跳（hop）与活动流事件。',
    focus_task: '焦点任务',
    activity: '活动流',
    events: '事件',
    waiting: '等待网格事件…',
    recent_tasks: '最近任务',
    no_tasks: '尚无已完成的网格任务。',
    hops: '跳',
    spent: '已花费',
    verified_agents: '已验证智能体',
    trust: '信任',
    stats_agents: '已验证智能体',
    stats_tasks: '任务（24小时）',
    stats_hops: '网格跳（24小时）',
    stats_success: '成功率',
    stats_volume: '成交额（24小时）',
    hub: 'Mesh Core',
    hub_sub: '零信任路由器',
    foot_stats: '/v1/stats',
  },
};

export function normalizeLocale(raw: string | null | undefined): UiLocale {
  const base = (raw || 'en').slice(0, 2).toLowerCase();
  return (SUPPORTED_UI_LOCALES as readonly string[]).includes(base)
    ? (base as UiLocale)
    : 'en';
}

export function readStoredLocale(): UiLocale {
  try {
    return normalizeLocale(localStorage.getItem(LANG_STORAGE_KEY));
  } catch {
    return normalizeLocale(typeof navigator !== 'undefined' ? navigator.language : 'en');
  }
}

export function writeStoredLocale(lang: UiLocale): void {
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
}

export function translate(lang: UiLocale, key: string): string {
  return I18N[lang]?.[key] || I18N.en[key] || key;
}
