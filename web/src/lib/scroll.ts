/**
 * Walking the reader to whatever comes next.
 *
 * The controls run down a long column, so after a choice the page moves to the next thing rather
 * than leaving the reader to find it. A step forward through a form runs only when its target is not
 * already fully in view, because scrolling somebody to what they are looking at reads as a twitch. A
 * choice that changes what the page is about walks whatever was showing, so the thing it opened
 * starts at the top of the screen rather than halfway down it.
 *
 * It starts at once and follows its target. The choice that asked for it usually sets off a flow,
 * and where that flow moves the target the page is aimed again as it travels rather than corrected
 * once everything has stopped. So a target the flow leaves where it is costs no wait at all, and one
 * it carries is followed rather than jumped to at the end.
 *
 * Focus never moves with the page.
 */

import { tick } from 'svelte';
import { prefersReducedMotion } from 'svelte/motion';

import { MOTION, MOTION_SLOW } from '$lib/motion';

/** Which edge of the target the page is brought to, as `scrollIntoView` reads it. */
type Block = 'start' | 'end';

/** How long the page takes to cover all but a twentieth of the distance to its destination. */
const TRAVEL = MOTION_SLOW;

/** Close enough that one eased step would round to nothing, so what is left is closed in one. */
const SNAP = 2;

/**
 * How long past the end of its flow a walk keeps following, so a target that never settles cannot
 * hold the page.
 */
const LIMIT = 2000;

/** How long a flow handed over as a promise is waited on before the page stops following it. */
const FLOW_LIMIT = 10000;

const length = (value: string) => (Number.isNaN(parseFloat(value)) ? 0 : parseFloat(value));

/**
 * What the target's chosen edge is offset by where it comes to rest: its own scroll margin, and the
 * room the page keeps clear for the header. Both hold still for the whole walk, so they are read
 * once rather than every frame.
 */
function resting(target: HTMLElement, block: Block): number {
	const own = getComputedStyle(target);
	const root = getComputedStyle(document.documentElement);

	return block === 'start'
		? -length(own.scrollMarginTop) - length(root.scrollPaddingTop)
		: length(own.scrollMarginBottom) + length(root.scrollPaddingBottom);
}

/**
 * Where the page has to sit for the target to rest at `block`, which is where `scrollIntoView` would
 * put it. It is worked out rather than handed to the browser because a smooth scroll is aimed once,
 * and this one is aimed again every frame.
 */
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
	/** Which edge of the target the page is brought to. */
	block: Block;
	/**
	 * The flow the choice set off, as how long it lasts or as the flow itself. The wait it buys costs
	 * nothing where the target does not move, because the page is already on its way by then.
	 *
	 * A request is a flow of unknown length, so it is handed over as its own promise and the page
	 * follows the target until it settles and for one motion after it, which is what the answer
	 * landing takes to lay itself out. Without that the page stops where the target used to be and
	 * whatever the answer moves is left showing instead of it.
	 */
	flowing?: number | Promise<unknown>;
	/**
	 * Walk even where the target is already fully in view.
	 *
	 * A step forward through a form only wants the page moved when the next thing is off screen. A
	 * choice that changes what the page is about wants the target put at the top of the screen
	 * whatever was showing before it, so nothing above it is left standing in the way.
	 */
	always?: boolean;
};

/**
 * Moves the page to the target and follows it for as long as the flow behind it runs.
 *
 * Awaiting it waits for the page to stop, which is what anything opening at the target needs.
 */
export async function walkTo(
	target: HTMLElement | undefined,
	{ block, flowing = MOTION, always = false }: Walk
): Promise<void> {
	if (!target) return;

	// The tick puts the choice in the page, so what is measured below is the page it made.
	await tick();

	const instant = prefersReducedMotion.current;
	const offset = resting(target, block);

	// When the flow is expected to be over, and the point past which the walk gives up whatever the
	// target is doing. A flow handed over as a promise sets both again the moment it settles.
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
		let travelling = false;

		// The reader taking the page over ends the walk, because the page is theirs from then on.
		const stop = () => {
			cancelAnimationFrame(frame);
			window.removeEventListener('wheel', stop);
			window.removeEventListener('touchmove', stop);
			resolve();
		};

		const step = (now: number) => {
			if (!target.isConnected || now > deadline) {
				stop();
				return;
			}

			const elapsed = now - last;
			last = now;

			// Not worth moving for yet. The flow can still push it off screen, so this keeps watching
			// until the flow is over rather than giving up on the first frame.
			if (!travelling && !always && fullyVisible(target)) {
				if (now >= following) stop();
				else frame = requestAnimationFrame(step);
				return;
			}

			travelling = true;

			const left = destination(target, block, offset) - window.scrollY;

			// Each frame closes the same share of whatever distance is left, so the page eases in on a
			// target standing still and keeps pace with one the flow is still moving.
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
