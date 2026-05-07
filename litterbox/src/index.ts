import { createArena } from './viz/arena';
import { createDashboard } from './viz/dashboard';
import { createSimCat } from './simcat/state-machine';
import { createAgent } from './agent/policy';
import { createEthicsMonitor } from './world/ethics-monitor';
import { createTickLoop } from './world/tick';
import { ARCHETYPES } from './simcat/archetypes';
import type { ArchetypeName, SimConfig } from './types';

const config: SimConfig = {
  tickRate: 10,
  simSpeed: 1,
  arenaWidth: 800,
  arenaHeight: 500,
};

async function main() {
  const canvas = document.getElementById('arena') as HTMLCanvasElement;
  canvas.width = config.arenaWidth;
  canvas.height = config.arenaHeight;

  const arena = await createArena(canvas, config);
  const dashboard = createDashboard();

  let currentArchetype: ArchetypeName = 'THE_CURIOUS_WATCHER';
  let simcat = createSimCat(ARCHETYPES[currentArchetype], config);
  let ethicsMonitor = createEthicsMonitor(currentArchetype);
  let agent = createAgent();

  const loop = createTickLoop(config, simcat, agent, ethicsMonitor, arena, dashboard);

  // Controls
  const archetypeSelect = document.getElementById('archetype-select') as HTMLSelectElement;
  archetypeSelect.addEventListener('change', () => {
    currentArchetype = archetypeSelect.value as ArchetypeName;
    simcat = createSimCat(ARCHETYPES[currentArchetype], config);
    ethicsMonitor = createEthicsMonitor(currentArchetype);
    loop.reset(simcat, ethicsMonitor);
  });

  const speedSelect = document.getElementById('speed-select') as HTMLSelectElement;
  speedSelect.addEventListener('change', () => {
    config.simSpeed = parseInt(speedSelect.value, 10);
  });

  document.getElementById('btn-pause')!.addEventListener('click', () => {
    loop.togglePause();
    const btn = document.getElementById('btn-pause')!;
    btn.textContent = loop.isPaused() ? 'Resume' : 'Pause';
  });

  document.getElementById('btn-reset')!.addEventListener('click', () => {
    simcat = createSimCat(ARCHETYPES[currentArchetype], config);
    ethicsMonitor = createEthicsMonitor(currentArchetype);
    loop.reset(simcat, ethicsMonitor);
  });

  document.getElementById('btn-export')!.addEventListener('click', () => {
    const data = ethicsMonitor.exportSession();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chatcat-session-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  loop.start();
}

main();
