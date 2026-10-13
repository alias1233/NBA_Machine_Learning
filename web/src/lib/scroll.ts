import { tick } from 'svelte';
import { prefersReducedMotion } from 'svelte/motion';

import { MOTION, MOTION_SLOW } from '$lib/motion';

/** Edge of the target to align to. Same values as `scrollIntoView`. */
type Block = 'start' | 'end';

/** Milliseconds the page takes to cover 95% of the distance. */
const TRAVEL = MOTION_SLOW;

/** Distance in pixels below which the page jumps straight to the target. */
const SNAP = 4;

/** Maximum milliseconds a scroll keeps following its target after the transition ends. */
const LIMIT = 2000;

/** Maximum milliseconds to wait for a transition passed as a promise. */
const FLOW_LIMIT = 10000;

/** Stops the automatic scroll in progress. Only one runs at a time, and a new one replaces the old one. */
let stopCurrentWalk: (() => void) | undefined;
let walkVersion = 0;

/** Stops the current automatic scroll and leaves the page where it is. */
export function stopWalking(): void {
	walkVersion += 1;
	stopCurrentWalk?.();
}

const length = (value: string) => (Number.isNaN(parseFloat(value)) ? 0 : parseFloat(value));

/** Returns the offset to keep at the target's edge, from its scroll margin and the root's scroll padding. */
function resting(target: HTMLElement, block: Block): number {
	const own = getComputedStyle(target);
	const root = getComputedStyle(document.documentElement);

	return block === 'start'
		? -length(own.scrollMarginTop) - length(root.scrollPaddingTop)
		: length(own.scrollMarginBottom) + length(root.scrollPaddingBottom);
}

/** Returns the scroll position that aligns the target to `block`. */
function destination(target: HTMLElement, block: Block, offset: number): number {
	const box = target.getBoundingClientRect();
	const edge = block === 'start' ? box.top : box.bottom - window.innerHeight;
	const furthest = document.documentElement.scrollHeight - window.innerHeight;

	return Math.min(Math.max(window.scrollY + edge + offset, 0), Math.max(furthest, 0));
}

function fullyVisible(target: HTMLElement): boolean {
	const box = target.getBoundingClientRect();

	return box.top >= 0 && box.bottom <= window.innerHeight;
}

type Walk = {
	block: Block;
	/** The transition to follow. Either its duration in milliseconds or a promise that settles when it ends. */
	flowing?: number | Promise<unknown>;
	/** Scrolls even if the target is already fully visible. */
	always?: boolean;
};

/** Scrolls the page to the target and keeps following it while a transition is running. */
export async function walkTo(
	target: HTMLElement | undefined,
	{ block, flowing = MOTION, always = false }: Walk
): Promise<void> {
	if (!target) return;

	stopWalking();
	const version = walkVersion;

	// Waits for the DOM to update, so the measurements below use the new layout.
	await tick();
	if (version !== walkVersion) return;

	const instant = prefersReducedMotion.current;
	const offset = resting(target, block);

	const waiting = typeof flowing === 'number' ? (instant ? 0 : flowing) : FLOW_LIMIT;

	let following = performance.now() + waiting;
	let deadline = following + LIMIT;

	if (typeof flowing !== 'number') {
		const landed = () => {
			following = performance.now() + (instant ? 0 : MOTION);
			deadline = following + LIMIT;
		};

		flowing.then(landed, landed);
	}

	return new Promise((resolve) => {
		let frame = 0;
		let last = performance.now();
		let traveling = false;

		// Ends the scroll. Also called when the user scrolls by wheel or touch.
		const stop = () => {
			cancelAnimationFrame(frame);
			window.removeEventListener('wheel', stop);
			window.removeEventListener('touchmove', stop);
			if (stopCurrentWalk === stop) stopCurrentWalk = undefined;
			resolve();
		};

		stopCurrentWalk = stop;

		const step = (now: number) => {
			if (!target.isConnected || now > deadline) {
				stop();
				return;
			}

			const elapsed = now - last;
			last = now;

			if (!traveling && !always && fullyVisible(target)) {
				if (now >= following) stop();
				else frame = requestAnimationFrame(step);
				return;
			}

			traveling = true;

			const left = destination(target, block, offset) - window.scrollY;

			// Each frame covers a fraction of the remaining distance, based on the time elapsed.
			const closing =
				instant || Math.abs(left) < SNAP ? 1 : 1 - Math.exp((-3 * elapsed) / TRAVEL);

			window.scrollBy({ top: left * closing, behavior: 'instant' });

			if (closing === 1 && now >= following) stop();
			else frame = requestAnimationFrame(step);
		};

		frame = requestAnimationFrame(step);

		window.addEventListener('wheel', stop, { passive: true });
		window.addEventListener('touchmove', stop, { passive: true });
	});
}
