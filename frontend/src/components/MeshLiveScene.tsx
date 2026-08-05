import { useEffect, useMemo, useRef, useState } from 'react';
import type { ActivityEvent, Agent, Task } from '../lib/api';
import { useLocale } from '../i18n/LocaleContext';

type Pt = { x: number; y: number };

type Node = {
  id: string;
  label: string;
  sub: string;
  trust: number;
  caps: string[];
  color: string;
  pos: Pt;
  isHub?: boolean;
};

type Particle = {
  id: number;
  from: Pt;
  to: Pt;
  t: number;
  speed: number;
  color: string;
  trail: boolean;
};

const W = 960;
const H = 540;
const CX = W / 2;
const CY = H / 2 + 8;

const CAP_COLORS: Record<string, string> = {
  research: '#1ec9a8',
  summarize: '#5eead4',
  oracle: '#f0a33a',
  verify: '#fbbf24',
  escrow: '#38bdf8',
  settle: '#818cf8',
};

function colorForCaps(caps: string[]): string {
  for (const c of caps) {
    const hit = CAP_COLORS[c.toLowerCase()];
    if (hit) return hit;
  }
  return '#94a3b8';
}

function kindColor(kind: string): string {
  if (kind.includes('settle') || kind.includes('invoke')) return '#34d399';
  if (kind.includes('escrow')) return '#fbbf24';
  if (kind.includes('verif')) return '#38bdf8';
  if (kind.includes('error')) return '#fb7185';
  if (kind.includes('discovery') || kind.includes('task')) return '#a78bfa';
  return '#22d3ee';
}

function agentLayout(agents: Agent[], hubLabel: string, hubSub: string): Node[] {
  const hub: Node = {
    id: 'hub',
    label: hubLabel,
    sub: hubSub,
    trust: 1,
    caps: [],
    color: '#22d3ee',
    pos: { x: CX, y: CY },
    isHub: true,
  };
  if (!agents.length) return [hub];

  const n = agents.length;
  const nodes: Node[] = [hub];
  agents.forEach((a, i) => {
    const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
    const orbit = 168 + (1 - a.trust_score) * 36;
    nodes.push({
      id: a.id,
      label: a.name,
      sub: a.capabilities.slice(0, 2).join(' · ') || a.status,
      trust: a.trust_score,
      caps: a.capabilities,
      color: colorForCaps(a.capabilities),
      pos: {
        x: CX + Math.cos(angle) * orbit,
        y: CY + Math.sin(angle) * (orbit * 0.72),
      },
    });
  });
  return nodes;
}

function lerp(a: Pt, b: Pt, t: number): Pt {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function shortName(name: string) {
  const parts = name.trim().split(/\s+/);
  return parts.length > 1 ? parts[0] : name.slice(0, 12);
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

export function MeshLiveScene({
  agents,
  tasks,
  activity,
  focusTaskId,
  onSelectTask,
}: {
  agents: Agent[];
  tasks: Task[];
  activity: ActivityEvent[];
  focusTaskId?: string | null;
  onSelectTask?: (id: string) => void;
}) {
  const { t } = useLocale();
  const nodes = useMemo(
    () => agentLayout(agents, t('hub'), t('hub_sub')),
    [agents, t],
  );
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const focusTask = useMemo(
    () => tasks.find((task) => task.id === focusTaskId) ?? tasks[0] ?? null,
    [tasks, focusTaskId],
  );

  const [hot, setHot] = useState<Record<string, number>>({});
  const [hover, setHover] = useState<string | null>(null);
  const particles = useRef<Particle[]>([]);
  const nextId = useRef(1);
  const lastAct = useRef<string | null>(null);
  const hopReplay = useRef(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const raf = useRef(0);

  // Pulse agents from live activity
  useEffect(() => {
    if (!activity.length) return;
    const latest = activity[activity.length - 1];
    if (!latest || latest.id === lastAct.current) return;
    lastAct.current = latest.id;
    const aid = latest.agent_id;
    if (aid) {
      setHot((h) => ({ ...h, [aid]: performance.now() }));
      const agent = byId.get(aid);
      const hub = byId.get('hub');
      if (agent && hub) {
        const outbound = latest.kind.includes('settle') || latest.kind.includes('invoke');
        particles.current.push({
          id: nextId.current++,
          from: outbound ? hub.pos : agent.pos,
          to: outbound ? agent.pos : hub.pos,
          t: 0,
          speed: 0.012 + Math.random() * 0.008,
          color: kindColor(latest.kind),
          trail: true,
        });
      }
    } else {
      setHot((h) => ({ ...h, hub: performance.now() }));
    }
  }, [activity, byId]);

  // Replay hops of focused task as packets
  useEffect(() => {
    if (!focusTask?.hops?.length) return;
    hopReplay.current = 0;
    const hub = byId.get('hub');
    if (!hub) return;
    const hops = focusTask.hops;
    let i = 0;
    const timer = window.setInterval(() => {
      if (i >= hops.length) {
        window.clearInterval(timer);
        return;
      }
      const hop = hops[i++];
      const agent = byId.get(hop.agent_id || '') ?? [...byId.values()].find((n) => n.label === hop.agent_name);
      if (!agent) return;
      setHot((h) => ({ ...h, [agent.id]: performance.now() }));
      particles.current.push({
        id: nextId.current++,
        from: hub.pos,
        to: agent.pos,
        t: 0,
        speed: 0.018,
        color: hop.success ? kindColor(`mesh.${hop.phase}`) : '#fb7185',
        trail: true,
      });
    }, 520);
    return () => window.clearInterval(timer);
  }, [focusTask?.id, byId]);

  // Ambient idle traffic so the graph feels alive
  useEffect(() => {
    if (agents.length === 0) return;
    const id = window.setInterval(() => {
      const hub = byId.get('hub');
      const peers = nodes.filter((n) => !n.isHub);
      if (!hub || !peers.length) return;
      const peer = peers[Math.floor(Math.random() * peers.length)];
      const out = Math.random() > 0.45;
      particles.current.push({
        id: nextId.current++,
        from: out ? hub.pos : peer.pos,
        to: out ? peer.pos : hub.pos,
        t: 0,
        speed: 0.006 + Math.random() * 0.004,
        color: `${peer.color}99`,
        trail: false,
      });
      if (particles.current.length > 48) {
        particles.current = particles.current.slice(-36);
      }
    }, 1400);
    return () => window.clearInterval(id);
  }, [agents.length, byId, nodes]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const draw = () => {
      ctx.clearRect(0, 0, W, H);

      // soft vignette
      const g = ctx.createRadialGradient(CX, CY, 40, CX, CY, 320);
      g.addColorStop(0, 'rgba(30,201,168,0.07)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      // orbit rings
      ctx.strokeStyle = 'rgba(30,201,168,0.08)';
      ctx.lineWidth = 1;
      for (const r of [110, 170, 230]) {
        ctx.beginPath();
        ctx.ellipse(CX, CY, r, r * 0.72, 0, 0, Math.PI * 2);
        ctx.stroke();
      }

      const hub = byId.get('hub');
      const now = performance.now();

      // edges hub → agents
      for (const n of nodes) {
        if (n.isHub || !hub) continue;
        const pulse = hot[n.id] && now - hot[n.id] < 1600;
        ctx.beginPath();
        ctx.moveTo(hub.pos.x, hub.pos.y);
        ctx.lineTo(n.pos.x, n.pos.y);
        ctx.strokeStyle = pulse ? `${n.color}88` : 'rgba(148,163,184,0.18)';
        ctx.lineWidth = pulse ? 2.2 : 1;
        ctx.stroke();
      }

      // particles
      const alive: Particle[] = [];
      for (const p of particles.current) {
        p.t += p.speed;
        if (p.t > 1) continue;
        alive.push(p);
        const pt = lerp(p.from, p.to, p.t);
        if (p.trail) {
          const back = lerp(p.from, p.to, Math.max(0, p.t - 0.12));
          ctx.beginPath();
          ctx.moveTo(back.x, back.y);
          ctx.lineTo(pt.x, pt.y);
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = 0.55;
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, p.trail ? 3.4 : 2.2, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = p.trail ? 12 : 4;
        ctx.fill();
        ctx.shadowBlur = 0;
      }
      particles.current = alive;

      // nodes
      for (const n of nodes) {
        const age = hot[n.id] ? now - hot[n.id] : 99999;
        const glow = age < 1800 ? 1 - age / 1800 : 0;
        const r = n.isHub ? 18 : 10 + n.trust * 6;
        const isHover = hover === n.id;

        ctx.beginPath();
        ctx.arc(n.pos.x, n.pos.y, r + 10 + glow * 8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(30, 201, 168, ${0.06 + glow * 0.22})`;
        if (!n.isHub) {
          const rgb = hexToRgb(n.color);
          if (rgb) ctx.fillStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},${0.08 + glow * 0.28})`;
        }
        ctx.fill();

        ctx.beginPath();
        ctx.arc(n.pos.x, n.pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = n.isHub ? '#0a1f1c' : '#071412';
        ctx.fill();
        ctx.lineWidth = isHover ? 2.5 : 1.5;
        ctx.strokeStyle = n.color;
        ctx.stroke();

        if (!n.isHub) {
          // trust arc
          ctx.beginPath();
          ctx.arc(n.pos.x, n.pos.y, r + 4, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * n.trust);
          ctx.strokeStyle = n.color;
          ctx.lineWidth = 2;
          ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.arc(n.pos.x, n.pos.y, 5, 0, Math.PI * 2);
          ctx.fillStyle = n.color;
          ctx.fill();
        }

        ctx.fillStyle = '#e2e8f0';
        ctx.font = n.isHub ? '600 13px Syne, system-ui' : '600 12px Syne, system-ui';
        ctx.textAlign = 'center';
        ctx.fillText(n.isHub ? n.label : shortName(n.label), n.pos.x, n.pos.y + r + 18);
        ctx.fillStyle = '#64748b';
        ctx.font = '500 10px "IBM Plex Sans", system-ui';
        ctx.fillText(n.sub.slice(0, 28), n.pos.x, n.pos.y + r + 32);
      }

      raf.current = requestAnimationFrame(draw);
    };

    raf.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf.current);
  }, [nodes, byId, hot, hover]);

  const hitTest = (clientX: number, clientY: number, el: HTMLCanvasElement) => {
    const rect = el.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * W;
    const y = ((clientY - rect.top) / rect.height) * H;
    for (const n of [...nodes].reverse()) {
      const r = n.isHub ? 22 : 16;
      const dx = n.pos.x - x;
      const dy = n.pos.y - y;
      if (dx * dx + dy * dy <= r * r) return n.id;
    }
    return null;
  };

  const hovered = hover ? byId.get(hover) : null;

  return (
    <section className="relative overflow-hidden rounded-none border-y border-teal-500/15 bg-[#041210]/[0.65]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(30,201,168,0.08),transparent_60%)]" />
      <div className="relative mx-auto max-w-7xl px-4 pt-5 pb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-teal-400/90">
            {t('live_mesh')}
          </p>
          <h2 className="font-display text-xl md:text-2xl font-bold text-white">
            {t('topology')} · {agents.length}{' '}
            {agents.length === 1 ? t('peers_one') : t('peers_many')}
          </h2>
          <p className="text-sm text-slate-400 mt-1">{t('packets_hint')}</p>
        </div>
        {focusTask && (
          <button
            type="button"
            onClick={() => onSelectTask?.(focusTask.id)}
            className="text-left rounded-xl border border-white/10 bg-black/30 px-4 py-2 max-w-md hover:border-teal-400/40 transition"
          >
            <p className="text-[10px] uppercase tracking-wider text-slate-500">{t('focus_task')}</p>
            <p className="text-sm text-slate-200 line-clamp-1">{focusTask.intent}</p>
            <p className="text-[11px] font-mono text-teal-300/80 mt-0.5">
              {focusTask.status} · {focusTask.hops.length} {t('hops')} · $
              {focusTask.total_spent_usd.toFixed(2)}
            </p>
          </button>
        )}
      </div>

      <div className="relative mx-auto max-w-7xl px-2 md:px-4 pb-4">
        <canvas
          ref={canvasRef}
          className="w-full h-auto max-h-[min(62vh,540px)] cursor-crosshair"
          style={{ aspectRatio: `${W} / ${H}` }}
          onMouseMove={(e) => setHover(hitTest(e.clientX, e.clientY, e.currentTarget))}
          onMouseLeave={() => setHover(null)}
        />
        {hovered && !hovered.isHub && (
          <div className="pointer-events-none absolute left-6 bottom-8 rounded-xl border border-white/10 bg-black/70 backdrop-blur px-4 py-3 max-w-xs">
            <p className="font-display text-sm text-white">{hovered.label}</p>
            <p className="text-xs text-slate-400 mt-1">{hovered.sub}</p>
            <p className="text-[11px] font-mono text-teal-300 mt-2">
              {t('trust')} {(hovered.trust * 100).toFixed(0)}% · {hovered.id}
            </p>
          </div>
        )}
      </div>

      {focusTask && focusTask.hops.length > 0 && (
        <div className="mx-auto max-w-7xl px-4 pb-5">
          <div className="flex flex-wrap gap-2">
            {focusTask.hops.map((h, i) => (
              <span
                key={`${focusTask.id}-${i}`}
                className={`text-[10px] font-mono uppercase tracking-wide px-2.5 py-1 rounded-md border ${
                  h.success
                    ? 'border-teal-500/30 text-teal-200 bg-teal-500/10'
                    : 'border-rose-500/30 text-rose-200 bg-rose-500/10'
                }`}
              >
                {h.phase}
                <span className="text-slate-500 mx-1">→</span>
                {h.agent_name.split(' ')[0]}
                <span className="text-slate-500 ml-1">{h.latency_ms}ms</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
