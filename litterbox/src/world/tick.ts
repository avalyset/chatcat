/**
 * Tick loop — coordinates SimCat, Agent, and Ethics Monitor per tick.
 * Runs at config.tickRate Hz, scaled by config.simSpeed.
 *
 * Uses the shared TickRunner for pure simulation logic; this module
 * adds browser timing (requestAnimationFrame) and visualisation updates.
 */

import type { SimConfig } from '../types';
import type { SimCat } from '../simcat/state-machine';
import type { ChatCatAgent } from '../agent/policy';
import type { EthicsMonitor } from './ethics-monitor';
import type { ArenaRenderer } from '../viz/arena';
import type { DashboardUpdater } from '../viz/dashboard';
import { createLogger, type Logger } from './logger';
import { createTickRunner, type TickRunner } from './tick-runner';

export interface TickLoop {
  start(): void;
  stop(): void;
  togglePause(): void;
  isPaused(): boolean;
  reset(simcat: SimCat, ethicsMonitor: EthicsMonitor): void;
}

export function createTickLoop(
  config: SimConfig,
  initialSimcat: SimCat,
  agent: ChatCatAgent,
  initialEthicsMonitor: EthicsMonitor,
  arena: ArenaRenderer,
  dashboard: DashboardUpdater
): TickLoop {
  let simcat = initialSimcat;
  let ethicsMonitor = initialEthicsMonitor;
  let logger: Logger = createLogger();
  let tickRunner: TickRunner = createTickRunner(simcat, agent, ethicsMonitor, logger);
  let paused = false;
  let animationId: number | null = null;
  let tickAccumulator = 0;
  let lastTimestamp = 0;

  function processTick(): void {
    const { catState, agentAction, intervention } = tickRunner.runOneTick();
    arena.update(catState, agentAction);
    dashboard.update(catState, agentAction, ethicsMonitor.getState(), agent.getExplanation(), intervention);
  }

  function loop(timestamp: number): void {
    if (paused) {
      lastTimestamp = timestamp;
      animationId = requestAnimationFrame(loop);
      return;
    }

    if (lastTimestamp === 0) lastTimestamp = timestamp;
    const dt = (timestamp - lastTimestamp) / 1000; // seconds
    lastTimestamp = timestamp;

    // Accumulate ticks based on real time and sim speed
    tickAccumulator += dt * config.tickRate * config.simSpeed;

    // Process accumulated ticks (cap to prevent spiral)
    const maxTicksPerFrame = Math.min(Math.floor(tickAccumulator), config.tickRate * config.simSpeed);
    for (let i = 0; i < maxTicksPerFrame; i++) {
      processTick();
      tickAccumulator--;
    }
    tickAccumulator = Math.max(0, tickAccumulator);

    animationId = requestAnimationFrame(loop);
  }

  function start(): void {
    lastTimestamp = 0;
    animationId = requestAnimationFrame(loop);
  }

  function stop(): void {
    if (animationId !== null) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
  }

  function togglePause(): void {
    paused = !paused;
  }

  function isPausedFn(): boolean {
    return paused;
  }

  function reset(newSimcat: SimCat, newEthicsMonitor: EthicsMonitor): void {
    simcat = newSimcat;
    ethicsMonitor = newEthicsMonitor;
    agent.reset();
    logger = createLogger();
    tickRunner = createTickRunner(simcat, agent, ethicsMonitor, logger);
    tickAccumulator = 0;
    lastTimestamp = 0;
  }

  return { start, stop, togglePause, isPaused: isPausedFn, reset };
}
