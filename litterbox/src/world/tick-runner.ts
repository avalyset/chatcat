/**
 * Headless TickRunner — pure simulation tick without rendering.
 *
 * Shared by both the browser tick loop (with Pixi.js viz) and
 * the headless batch CLI. Contains no rendering side effects.
 */

import type { CatState, AgentAction } from '../types';
import type { SimCat } from '../simcat/state-machine';
import type { ChatCatAgent } from '../agent/policy';
import type { EthicsMonitor, EthicsIntervention } from './ethics-monitor';
import type { Logger } from './logger';
import { idle, pause as pauseAction } from '../agent/actions';

export interface TickResult {
  catState: CatState;
  agentAction: AgentAction;
  intervention: EthicsIntervention;
}

export interface TickRunner {
  runOneTick(): TickResult;
}

export function createTickRunner(
  simcat: SimCat,
  agent: ChatCatAgent,
  ethicsMonitor: EthicsMonitor,
  logger?: Logger
): TickRunner {
  function runOneTick(): TickResult {
    let agentAction = agent.decide(simcat.getState());
    const catState = simcat.tick(agentAction);
    const intervention = ethicsMonitor.onTick(catState, agentAction);

    if (intervention.lockSession) {
      agentAction = idle();
    } else if (intervention.forcePause) {
      agentAction = pauseAction(intervention.pauseDuration_ms);
    } else if (intervention.dailyCapReached) {
      agentAction = idle();
    }

    if (logger) {
      logger.log(catState.tickCount, catState, agentAction, intervention);
    }

    return { catState, agentAction, intervention };
  }

  return { runOneTick };
}
