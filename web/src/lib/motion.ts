/**
 * Motion a script has to take part in, rather than hand to CSS.
 *
 * These mirror `app.css`, because neither a tween, a two-phase reveal nor a timer can read a
 * duration out of a stylesheet. Reduced motion drops a roll to nothing, which stops the animation
 * without stopping the change itself.
 */

import { cubicOut } from 'svelte/easing';
import { Tween, prefersReducedMotion } from 'svelte/motion';
import { fade, slide } from 'svelte/transition';

import type { TransitionConfig } from 'svelte/transition';

/** `--motion`. A rolling figure, a region opening, and the first phase of the answer column reveal. */
export const MOTION = 200;

/** `--motion-slow`. The chart drawing in, and the line the answer column opens with. */
export const MOTION_SLOW = 320;

/** `--motion-reveal`. The answer column widening. */
export const MOTION_REVEAL = 700;

/** `--ease-in` as a curve a script can run. Both cover half the distance in the first fifth of it. */
const EASE = cubicOut;

const timed = (duration: number) => (prefersReducedMotion.current ? 0 : duration);

export const rolling = (value: () => number) => Tween.of(value, { duration: () => timed(MOTION) });

/**
 * A region of the page opening or closing, and the one motion for it. The room it takes flows, so
 * the page under it is carried rather than thrown.
 */
export function flow(node: Element, { duration = MOTION } = {}): TransitionConfig {
	const room = slide(node, { duration: timed(duration), easing: EASE });

	// Sliding alone holds the contents at full opacity, which reads as a wipe. The fade over the top
	// is what makes it a reveal.
	return { ...room, css: (t, u) => `${room.css?.(t, u) ?? ''} opacity: ${t};` };
}

/**
 * Holds a container at the height of its contents, so a swap inside it flows rather than changing
 * size in one frame. The first child is measured, because the container is what the height is
 * written to, and the container carries the height transition in its own stylesheet.
 */
export function flowingHeight(node: HTMLElement) {
	const content = node.firstElementChild;

	if (!content) return;

	// The first write is `auto` to a length, which does not interpolate, so the opening size lands
	// rather than flowing out of nothing.
	const observer = new ResizeObserver(([entry]) => {
		node.style.height = `${entry.borderBoxSize[0].blockSize}px`;
	});

	observer.observe(content);

	return { destroy: () => observer.disconnect() };
}

/** A floating panel arriving. It changes nothing under it, so it fades where it stands. */
export const appear = (node: Element, { duration = MOTION } = {}): TransitionConfig =>
	fade(node, { duration: timed(duration) });

/** Waits for a flow to land, so whatever measures the page next measures where it settles. */
export const settled = (duration = MOTION) =>
	new Promise<void>((resolve) => setTimeout(resolve, timed(duration)));
