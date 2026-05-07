/**
 * Dashboard — side panel updating live stats.
 * Exposes everything the ethics monitor sees. Transparency is the feature.
 */

import type { AgentAction, CatState, EthicsState, FelineFive } from '../types';
import type { EthicsIntervention } from '../world/ethics-monitor';
import { ARCHETYPES } from '../simcat/archetypes';

export interface DashboardUpdater {
  update(
    catState: CatState,
    agentAction: AgentAction,
    ethicsState: EthicsState,
    explanation: string,
    intervention: EthicsIntervention
  ): void;
}

const CSS_COLORS = [
  '#4caf50', // 1 — green
  '#8bc34a', // 2
  '#cddc39', // 3
  '#ffeb3b', // 4
  '#ff9800', // 5
  '#f44336', // 6
  '#d32f2f', // 7
];

export function createDashboard(): DashboardUpdater {
  const cssValueEl = document.getElementById('css-value')!;
  const cssBarEl = document.getElementById('css-bar')!;
  const catStateEl = document.getElementById('cat-state')!;
  const sessionTimeEl = document.getElementById('session-time')!;
  const sessionCapEl = document.getElementById('session-cap')!;
  const optOutEl = document.getElementById('opt-out-count')!;
  const forcedPausesEl = document.getElementById('forced-pauses')!;
  const actionLogEl = document.getElementById('action-log')!;
  const policyEl = document.getElementById('policy-explanation')!;
  const radarCanvas = document.getElementById('radar') as HTMLCanvasElement;

  const actionHistory: string[] = [];
  let lastRadarArchetype = '';

  function update(
    catState: CatState,
    agentAction: AgentAction,
    ethicsState: EthicsState,
    explanation: string,
    intervention: EthicsIntervention
  ): void {
    // CSS
    const cssInt = Math.round(catState.cssScore);
    cssValueEl.textContent = catState.cssScore.toFixed(1);
    const pct = ((catState.cssScore - 1) / 6) * 100;
    cssBarEl.style.width = `${Math.max(5, pct)}%`;
    cssBarEl.style.background = CSS_COLORS[Math.min(cssInt - 1, 6)];

    // Cat state
    catStateEl.textContent = catState.state;

    // Session time
    if (ethicsState.currentSessionLog) {
      const ticks = ethicsState.currentSessionLog.endTick - ethicsState.currentSessionLog.startTick;
      const seconds = Math.floor(ticks / 10);
      const min = Math.floor(seconds / 60);
      const sec = seconds % 60;
      sessionTimeEl.textContent = `${min}:${sec.toString().padStart(2, '0')}`;

      const capPct = Math.min(100, (ethicsState.dailySessionMinutes / ethicsState.dailyCapMinutes) * 100);
      sessionCapEl.textContent = `${capPct.toFixed(0)}%`;

      optOutEl.textContent = String(ethicsState.currentSessionLog.optOutEvents);
      forcedPausesEl.textContent = String(ethicsState.currentSessionLog.forcedPauses);
    }

    // Action log
    if (agentAction.type !== 'idle') {
      const entry = `[${catState.tickCount}] ${agentAction.type} @ ${agentAction.intensity.toFixed(2)}`;
      actionHistory.unshift(entry);
      if (actionHistory.length > 20) actionHistory.pop();
      actionLogEl.innerHTML = actionHistory.map(a => `<div>${a}</div>`).join('');
    }

    // Policy explanation
    let explanationText = explanation;
    if (intervention.reason) {
      explanationText = `[ETHICS] ${intervention.reason}`;
    }
    policyEl.textContent = explanationText;

    // Personality radar (only redraw on archetype change to save CPU)
    if (catState.archetype !== lastRadarArchetype) {
      lastRadarArchetype = catState.archetype;
      drawRadar(radarCanvas, ARCHETYPES[catState.archetype].personality, catState.archetype);
    }
  }

  return { update };
}

function drawRadar(canvas: HTMLCanvasElement, personality: FelineFive, label: string): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const r = Math.min(cx, cy) - 25;

  ctx.clearRect(0, 0, w, h);

  const dims = [
    { key: 'neuroticism', label: 'N' },
    { key: 'extraversion', label: 'E' },
    { key: 'dominance', label: 'D' },
    { key: 'impulsiveness', label: 'I' },
    { key: 'agreeableness', label: 'A' },
  ] as const;

  const n = dims.length;
  const angleStep = (Math.PI * 2) / n;

  // Grid circles
  ctx.strokeStyle = '#0f3460';
  ctx.lineWidth = 0.5;
  for (let i = 1; i <= 4; i++) {
    ctx.beginPath();
    const gr = (r * i) / 4;
    for (let j = 0; j <= n; j++) {
      const angle = j * angleStep - Math.PI / 2;
      const x = cx + Math.cos(angle) * gr;
      const y = cy + Math.sin(angle) * gr;
      j === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // Axes
  ctx.strokeStyle = '#0f3460';
  for (let i = 0; i < n; i++) {
    const angle = i * angleStep - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r);
    ctx.stroke();
  }

  // Values
  const values = dims.map(d => personality[d.key]);
  ctx.fillStyle = 'rgba(127, 187, 202, 0.3)';
  ctx.strokeStyle = '#7fbbca';
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const angle = i * angleStep - Math.PI / 2;
    const x = cx + Math.cos(angle) * r * values[i];
    const y = cy + Math.sin(angle) * r * values[i];
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Labels
  ctx.fillStyle = '#e0e0e0';
  ctx.font = '11px monospace';
  ctx.textAlign = 'center';
  for (let i = 0; i < n; i++) {
    const angle = i * angleStep - Math.PI / 2;
    const lx = cx + Math.cos(angle) * (r + 16);
    const ly = cy + Math.sin(angle) * (r + 16);
    ctx.fillText(dims[i].label, lx, ly + 4);
  }

  // Archetype name
  ctx.fillStyle = '#7fbbca';
  ctx.font = '9px monospace';
  ctx.fillText(label.replace(/_/g, ' '), cx, h - 4);
}
