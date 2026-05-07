/**
 * ChatCatAgent sprite — abstract form in cat-vision dichromatic palette.
 *
 * Cat vision: dichromatic, S-cone 460nm (blue) + ML-cone 556nm (yellow-green),
 * neutral point ~505nm. We use blue-yellow palette so the agent is maximally
 * visible to a real cat's visual system.
 * Source: Jacobs 1993, Loop et al. 1987
 *
 * NOT prey-shaped. Abstract form that can slow-blink (eye shape that closes
 * gradually). Position: corner of arena.
 */

import { Graphics, Container } from 'pixi.js';
import type { AgentAction } from '../types';

export interface AgentVisual {
  update(action: AgentAction, cssScore: number): void;
}

// Cat-vision palette (dichromatic: S-cone 460nm, ML-cone 556nm)
const BLUE = 0x3366cc;       // ~460nm S-cone
const YELLOW = 0xcccc44;     // ~556nm ML-cone
const NEUTRAL = 0x557788;    // ~505nm neutral point
const STRESS_RED = 0xcc4444; // Warning colour (for human observer, not cat)

export function drawAgent(container: Container): AgentVisual {
  const body = new Graphics();
  const eye = new Graphics();
  const indicator = new Graphics();

  container.addChild(body);
  container.addChild(eye);
  container.addChild(indicator);

  let blinkPhase = 0;

  function drawBody(): void {
    body.clear();
    // Abstract rounded form — NOT prey-shaped
    body.roundRect(-20, -25, 40, 50, 12);
    body.fill(BLUE);
    body.roundRect(-16, -21, 32, 42, 8);
    body.fill(YELLOW);
    body.roundRect(-12, -17, 24, 34, 6);
    body.fill(NEUTRAL);
  }

  function drawEye(openness: number): void {
    eye.clear();
    // Eye that can slow-blink (Humphrey et al. 2020 protocol)
    const eyeHeight = 8 * openness;
    if (eyeHeight > 0.5) {
      eye.ellipse(0, -5, 6, eyeHeight);
      eye.fill(YELLOW);
      // Pupil
      eye.circle(0, -5, 2 * openness);
      eye.fill(0x111133);
    } else {
      // Closed — line
      eye.moveTo(-6, -5);
      eye.lineTo(6, -5);
      eye.stroke({ color: YELLOW, width: 2 });
    }
  }

  function drawIndicator(cssScore: number): void {
    indicator.clear();
    // Small indicator light — for human observer
    const color = cssScore >= 5 ? STRESS_RED : cssScore >= 3 ? YELLOW : 0x44cc44;
    indicator.circle(0, 30, 4);
    indicator.fill(color);
  }

  function update(action: AgentAction, cssScore: number): void {
    drawBody();
    drawIndicator(cssScore);

    // Animate slow blink
    if (action.type === 'slow_blink') {
      // Half-blink → eye narrow → eye closure (Humphrey et al. 2020)
      blinkPhase = (blinkPhase + 0.05) % 1;
      const openness = blinkPhase < 0.3
        ? 1 - (blinkPhase / 0.3) * 0.5  // half-blink
        : blinkPhase < 0.6
          ? 0.5 - ((blinkPhase - 0.3) / 0.3) * 0.4  // eye narrow
          : blinkPhase < 0.8
            ? 0.1  // closed
            : 0.1 + ((blinkPhase - 0.8) / 0.2) * 0.9;  // reopen
      drawEye(openness);
    } else if (action.type === 'pause' || action.type === 'idle') {
      blinkPhase = 0;
      drawEye(0.7); // Relaxed, slightly narrowed
    } else if (action.type === 'side_glance') {
      blinkPhase = 0;
      // Offset eye slightly
      eye.clear();
      eye.ellipse(3, -5, 5, 6);
      eye.fill(YELLOW);
      eye.circle(4, -5, 2);
      eye.fill(0x111133);
    } else {
      blinkPhase = 0;
      drawEye(1); // Fully open
    }
  }

  // Initial
  drawBody();
  drawEye(0.7);
  drawIndicator(1);

  return { update };
}
