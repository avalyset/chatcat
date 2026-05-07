/**
 * SimCat sprite — stylised 2D top-down cat shape.
 * Ear/tail/posture animated according to state.
 * Uses simple vector shapes — not trying to be realistic.
 * Neutral grey body; expressiveness via ear/tail/eye state.
 */

import { Graphics, Container } from 'pixi.js';
import type { CatState } from '../types';

export interface SimCatVisual {
  update(state: CatState): void;
}

export function drawSimCat(container: Container): SimCatVisual {
  const body = new Graphics();
  const ears = new Graphics();
  const tail = new Graphics();
  const eyes = new Graphics();

  container.addChild(tail);
  container.addChild(body);
  container.addChild(ears);
  container.addChild(eyes);

  function drawBody(posture: string): void {
    body.clear();
    const w = posture === 'arched' ? 28 : posture === 'crouched' ? 22 : 24;
    const h = posture === 'arched' ? 16 : posture === 'crouched' ? 10 : 14;
    body.ellipse(0, 0, w, h);
    body.fill(0x888899);
    // Head
    body.circle(w - 4, 0, 10);
    body.fill(0x888899);
  }

  function drawEars(earPos: string): void {
    ears.clear();
    const baseX = 18;
    const baseY = -6;

    switch (earPos) {
      case 'forward':
        ears.moveTo(baseX, baseY);
        ears.lineTo(baseX + 5, baseY - 12);
        ears.lineTo(baseX + 10, baseY);
        ears.fill(0xaaaabb);
        ears.moveTo(baseX, baseY);
        ears.lineTo(baseX - 5, baseY - 12);
        ears.lineTo(baseX - 10, baseY);
        ears.fill(0xaaaabb);
        break;
      case 'neutral':
        ears.moveTo(baseX, baseY);
        ears.lineTo(baseX + 7, baseY - 8);
        ears.lineTo(baseX + 12, baseY + 2);
        ears.fill(0xaaaabb);
        ears.moveTo(baseX, baseY);
        ears.lineTo(baseX - 7, baseY - 8);
        ears.lineTo(baseX - 12, baseY + 2);
        ears.fill(0xaaaabb);
        break;
      case 'sideways':
        ears.moveTo(baseX, baseY);
        ears.lineTo(baseX + 12, baseY - 4);
        ears.lineTo(baseX + 10, baseY + 4);
        ears.fill(0x999aaa);
        ears.moveTo(baseX, baseY);
        ears.lineTo(baseX - 12, baseY - 4);
        ears.lineTo(baseX - 10, baseY + 4);
        ears.fill(0x999aaa);
        break;
      case 'flat':
        ears.moveTo(baseX, baseY + 2);
        ears.lineTo(baseX + 14, baseY + 2);
        ears.lineTo(baseX + 10, baseY + 6);
        ears.fill(0x777788);
        ears.moveTo(baseX, baseY + 2);
        ears.lineTo(baseX - 14, baseY + 2);
        ears.lineTo(baseX - 10, baseY + 6);
        ears.fill(0x777788);
        break;
    }
  }

  function drawTail(tailPos: string): void {
    tail.clear();
    const startX = -24;
    const startY = 0;

    switch (tailPos) {
      case 'up':
        tail.moveTo(startX, startY);
        tail.quadraticCurveTo(startX - 15, startY - 30, startX - 5, startY - 40);
        tail.stroke({ color: 0x888899, width: 4 });
        break;
      case 'neutral':
        tail.moveTo(startX, startY);
        tail.quadraticCurveTo(startX - 20, startY + 5, startX - 35, startY - 5);
        tail.stroke({ color: 0x888899, width: 4 });
        break;
      case 'low':
        tail.moveTo(startX, startY);
        tail.quadraticCurveTo(startX - 15, startY + 15, startX - 30, startY + 20);
        tail.stroke({ color: 0x888899, width: 3 });
        break;
      case 'puffed':
        tail.moveTo(startX, startY);
        tail.quadraticCurveTo(startX - 10, startY - 20, startX - 5, startY - 30);
        tail.stroke({ color: 0x888899, width: 8 });
        break;
      case 'lashing':
        const t = Date.now() / 200;
        const lashX = Math.sin(t) * 15;
        tail.moveTo(startX, startY);
        tail.quadraticCurveTo(startX - 15 + lashX, startY + 5, startX - 30, startY);
        tail.stroke({ color: 0x888899, width: 4 });
        break;
    }
  }

  function drawEyes(pupilDilation: number, cssScore: number): void {
    eyes.clear();
    const eyeX = 22;
    const eyeY = -2;
    const eyeSpacing = 6;

    // Eye whites (slightly yellow-green — cat-like)
    const eyeColor = cssScore >= 5 ? 0xccaa44 : 0xbbcc66;
    const pupilSize = 2 + pupilDilation * 3;

    // Left eye
    eyes.ellipse(eyeX - eyeSpacing, eyeY, 4, 3);
    eyes.fill(eyeColor);
    eyes.circle(eyeX - eyeSpacing, eyeY, pupilSize);
    eyes.fill(0x111111);

    // Right eye
    eyes.ellipse(eyeX + eyeSpacing, eyeY, 4, 3);
    eyes.fill(eyeColor);
    eyes.circle(eyeX + eyeSpacing, eyeY, pupilSize);
    eyes.fill(0x111111);
  }

  function update(state: CatState): void {
    drawBody(state.bodyPosture);
    drawEars(state.earPosition);
    drawTail(state.tailPosition);
    drawEyes(state.pupilDilation, state.cssScore);
  }

  // Initial draw
  drawBody('relaxed');
  drawEars('neutral');
  drawTail('neutral');
  drawEyes(0.3, 1);

  return { update };
}
