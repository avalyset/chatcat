/**
 * Arena renderer — Pixi.js v8 canvas for the Litterbox.
 * 800×500 px arena with SimCat and ChatCatAgent sprites.
 */

import { Application, Graphics, Container, Text, TextStyle } from 'pixi.js';
import type { CatState, AgentAction, SimConfig } from '../types';
import { drawSimCat, type SimCatVisual } from './simcat-sprite';
import { drawAgent, type AgentVisual } from './agent-sprite';

export interface ArenaRenderer {
  update(catState: CatState, agentAction: AgentAction): void;
  destroy(): void;
}

export async function createArena(canvas: HTMLCanvasElement, config: SimConfig): Promise<ArenaRenderer> {
  const app = new Application();
  await app.init({
    canvas,
    width: config.arenaWidth,
    height: config.arenaHeight,
    background: 0x1a1a2e,
    antialias: true,
  });

  // Arena border
  const border = new Graphics();
  border.rect(0, 0, config.arenaWidth, config.arenaHeight);
  border.stroke({ color: 0x0f3460, width: 2 });
  app.stage.addChild(border);

  // Grid lines (subtle)
  const grid = new Graphics();
  for (let x = 0; x < config.arenaWidth; x += 50) {
    grid.moveTo(x, 0);
    grid.lineTo(x, config.arenaHeight);
  }
  for (let y = 0; y < config.arenaHeight; y += 50) {
    grid.moveTo(0, y);
    grid.lineTo(config.arenaWidth, y);
  }
  grid.stroke({ color: 0x0f3460, width: 0.5, alpha: 0.3 });
  app.stage.addChild(grid);

  // Zone label
  const labelStyle = new TextStyle({ fontSize: 10, fill: 0x333355, fontFamily: 'monospace' });
  const agentZoneLabel = new Text({ text: 'AGENT ZONE', style: labelStyle });
  agentZoneLabel.x = config.arenaWidth - 120;
  agentZoneLabel.y = 10;
  app.stage.addChild(agentZoneLabel);

  // SimCat visual
  const catContainer = new Container();
  app.stage.addChild(catContainer);
  const catVisual = drawSimCat(catContainer);

  // Agent visual
  const agentContainer = new Container();
  agentContainer.x = config.arenaWidth - 80;
  agentContainer.y = config.arenaHeight / 2;
  app.stage.addChild(agentContainer);
  const agentVisual = drawAgent(agentContainer);

  // State label on cat
  const catLabelStyle = new TextStyle({ fontSize: 9, fill: 0x7fbbca, fontFamily: 'monospace' });
  const catLabel = new Text({ text: '', style: catLabelStyle });
  catLabel.anchor.set(0.5, 0);
  app.stage.addChild(catLabel);

  function update(catState: CatState, agentAction: AgentAction): void {
    // Update cat position and appearance
    catContainer.x = catState.position.x;
    catContainer.y = catState.position.y;
    catContainer.visible = catState.state !== 'ABSENT';
    catVisual.update(catState);

    // Update cat label
    catLabel.text = catState.state;
    catLabel.x = catState.position.x;
    catLabel.y = catState.position.y + 30;
    catLabel.visible = catState.state !== 'ABSENT';

    // Update agent
    agentVisual.update(agentAction, catState.cssScore);
  }

  function destroy(): void {
    app.destroy();
  }

  return { update, destroy };
}
