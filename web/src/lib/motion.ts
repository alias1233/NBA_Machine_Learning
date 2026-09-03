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

/**
 * A duration, or none at all where the reader has asked for stillness.
 *
 * Exported because a Svelte animation is given a plain number rather than a transition of its own,
 * so a list rearranging under the reader has to ask this the same way every transition here does.
 */
export const timed = (duration: number) => (prefersReducedMotion.current ? 0 : duration);

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

/**
 * A card joining or leaving a hand the reader is narrowing.
 *
 * It fades and gives up a little of its size where it lies, so a card the search no longer answers
 * for is put back on the deck rather than deleted. It travels nowhere on its way out, because the
 * cards that stay are what moves: they close the gap it left, and that is what says the hand was
 * dealt again rather than redrawn.
 */
export const dealing = (_node: Element, { duration = MOTION } = {}): TransitionConfig => ({
	duration: timed(duration),
	easing: EASE,
	css: (t) => `opacity: ${t}; scale: ${0.94 + t * 0.06};`
});

/** Waits for a flow to land, so whatever measures the page next measures where it settles. */
export const settled = (duration = MOTION) =>
	new Promise<void>((resolve) => setTimeout(resolve, timed(duration)));

/** How far from a control a hand starts to count as reaching for it. */
const REACH = 220;

/**
 * How near the reader's hand is to a control, written on it for the stylesheet to draw with.
 *
 * `--hand` is 0 with the pointer a reach away and 1 with it on the control, and nothing says which
 * side the hand is on, because a control that moved toward the pointer would be answering it rather
 * than waiting for it. It is registered in `app.css`, which is what lets it transition rather than
 * jump between the values written here.
 *
 * A mouse only. Nothing follows a finger, and reduced motion leaves the control at rest, where
 * hover, focus and press still say everything they said before.
 */
export function nearHand(node: HTMLElement, reach = REACH) {
	let frame = 0;
	let pointer: { x: number; y: number } | null = null;

	/** Back to what the stylesheet alone says, with the hand still where it was last seen. */
	function clear() {
		node.style.removeProperty('--hand');
	}

	function rest() {
		pointer = null;
		clear();
	}

	function measure() {
		frame = 0;

		if (!pointer) return;

		const box = node.getBoundingClientRect();
		// To the nearest edge rather than to the centre, so a wide block is reached for across all of
		// itself instead of from one point in the middle of it.
		const away = Math.hypot(
			Math.max(box.left - pointer.x, 0, pointer.x - box.right),
			Math.max(box.top - pointer.y, 0, pointer.y - box.bottom)
		);

		if (away >= reach) return clear();

		node.style.setProperty('--hand', String(1 - away / reach));
	}

	function draw() {
		frame ||= requestAnimationFrame(measure);
	}

	function follow(event: PointerEvent) {
		if (event.pointerType !== 'mouse' || prefersReducedMotion.current) return rest();

		pointer = { x: event.clientX, y: event.clientY };
		draw();
	}

	// A still hand over a page that is scrolling is a hand the control is moving away from, so the
	// reach is measured again rather than left holding the last frame's answer.
	addEventListener('pointermove', follow, { passive: true });
	addEventListener('scroll', draw, { passive: true });
	addEventListener('blur', rest);

	return {
		destroy: () => {
			cancelAnimationFrame(frame);
			removeEventListener('pointermove', follow);
			removeEventListener('scroll', draw);
			removeEventListener('blur', rest);
		}
	};
}
