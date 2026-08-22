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

/** `--motion-slow`. How far the page travels to reach the answer. */
export const MOTION_SLOW = 320;

/** `--motion-impact`. The one authored entrance a prediction page earns. */
export const MOTION_IMPACT = 680;

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
 * Holds a container at the height of its only child, so a swap inside it flows rather than changing
 * size in one frame. It owns the motion of everything under it, so nothing inside one carries a
 * height transition of its own. The caller says what its overflow does and nothing else.
 *
 * One of these inside another follows the inner one frame by frame rather than chasing it, because
 * a transition of its own would trail the growth and clip whatever sits below.
 */
export function flowingHeight(node: HTMLElement) {
	const content = node.firstElementChild;

	if (!content) return;

	node.style.transitionProperty = 'height';
	node.style.transitionDuration = 'var(--motion)';
	node.style.transitionTimingFunction = 'var(--ease-in)';

	// The child is measured rather than the container, because the container is what the height is
	// written to. The first write is `auto` to a length, which does not interpolate, so the opening
	// size lands rather than flowing out of nothing.
	const observer = new ResizeObserver(([entry]) => {
		const { paddingTop, paddingBottom } = getComputedStyle(node);
		const padding = parseFloat(paddingTop) + parseFloat(paddingBottom);

		node.style.height = `${entry.borderBoxSize[0].blockSize + padding}px`;
	});

	observer.observe(content);

	let following: ReturnType<typeof setTimeout>;

	// A timer rather than a matching end event, because a container removed part way through its
	// flow never reports one and this one would stay instant for good.
	function follow(event: TransitionEvent) {
		if (event.target === node || event.propertyName !== 'height') return;

		node.style.transitionDuration = '0s';

		clearTimeout(following);
		following = setTimeout(() => (node.style.transitionDuration = 'var(--motion)'), MOTION);
	}

	node.addEventListener('transitionrun', follow);

	return {
		destroy: () => {
			observer.disconnect();
			clearTimeout(following);
			node.removeEventListener('transitionrun', follow);
		}
	};
}

/**
 * Something arriving or leaving where it stands, changing nothing under it. A floating panel, and
 * the reserved space an answer is printed over.
 */
export const appear = (node: Element, { duration = MOTION } = {}): TransitionConfig =>
	fade(node, { duration: timed(duration) });

/** Waits for a flow to land, so whatever measures the page next measures where it settles. */
export const settled = (duration = MOTION) =>
	new Promise<void>((resolve) => setTimeout(resolve, timed(duration)));
