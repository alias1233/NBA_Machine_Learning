import { cubicOut } from 'svelte/easing';
import { Tween, prefersReducedMotion } from 'svelte/motion';
import { fade, slide } from 'svelte/transition';

import type { TransitionConfig } from 'svelte/transition';

/** Matches `--motion` in CSS. */
export const MOTION = 200;

/** Matches `--motion-slow` in CSS. */
export const MOTION_SLOW = 320;

/** Matches `--motion-impact` in CSS. */
export const MOTION_IMPACT = 680;

/** JavaScript version of the `--ease-in` curve. */
const EASE = cubicOut;

/** Returns the duration, or 0 if the user prefers reduced motion. */
export const timed = (duration: number) => (prefersReducedMotion.current ? 0 : duration);

export const rolling = (value: () => number) => Tween.of(value, { duration: () => timed(MOTION) });

/** Transition for a section that opens or closes. Slides and fades. */
export function flow(node: Element, { duration = MOTION } = {}): TransitionConfig {
	const room = slide(node, { duration: timed(duration), easing: EASE });

	return { ...room, css: (t, u) => `${room.css?.(t, u) ?? ''} opacity: ${t};` };
}

/** Keeps a container at the height of its only child and animates height changes. */
export function flowingHeight(node: HTMLElement) {
	const content = node.firstElementChild;

	if (!content) return;

	node.style.transitionProperty = 'height';
	node.style.transitionDuration = 'var(--motion)';
	node.style.transitionTimingFunction = 'var(--ease-in)';

	const observer = new ResizeObserver(([entry]) => {
		const { paddingTop, paddingBottom } = getComputedStyle(node);
		const padding = parseFloat(paddingTop) + parseFloat(paddingBottom);

		node.style.height = `${entry.borderBoxSize[0].blockSize + padding}px`;
	});

	observer.observe(content);

	let following: ReturnType<typeof setTimeout>;

	// Uses a timer because transitionend does not fire if the element is removed mid-transition.
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

/** Fade transition for something that appears or disappears in place. */
export const appear = (node: Element, { duration = MOTION } = {}): TransitionConfig =>
	fade(node, { duration: timed(duration) });

/** Transition for a game card entering or leaving the list as it is filtered. */
export const dealing = (_node: Element, { duration = MOTION } = {}): TransitionConfig => ({
	duration: timed(duration),
	easing: EASE,
	css: (t) => `opacity: ${t}; scale: ${0.94 + t * 0.06};`
});

export const settled = (duration = MOTION) =>
	new Promise<void>((resolve) => setTimeout(resolve, timed(duration)));

/** Distance in pixels at which the pointer starts to count as near a control. */
const REACH = 220;

/** Sets `--hand` on the element to how close the pointer is, from 0 to 1, for CSS to use. */
export function nearHand(node: HTMLElement, reach = REACH) {
	let frame = 0;
	let pointer: { x: number; y: number } | null = null;

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
