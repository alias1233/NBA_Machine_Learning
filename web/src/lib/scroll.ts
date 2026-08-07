/**
 * Walking the reader to whatever comes next. See section 7, Guided scrolling.
 *
 * The controls run down a long column, so after a choice the page moves to the next thing rather
 * than leaving the reader to find it. A scroll runs only when its target is not already fully in
 * view, because scrolling somebody to what they are looking at reads as a twitch. R7.7 and R7.8.
 *
 * Focus never moves with the page. R12.11.
 */

import { tick } from 'svelte';
import { prefersReducedMotion } from 'svelte/motion';

/** The choice that asked for this usually moves the target, so it is measured once it has settled. */
export async function scrollIntoViewIfOffScreen(
	target: HTMLElement | undefined,
	block: 'start' | 'end'
): Promise<void> {
	if (!target) return;

	await tick();

	const box = target.getBoundingClientRect();

	if (box.top >= 0 && box.bottom <= window.innerHeight) return;

	target.scrollIntoView({
		behavior: prefersReducedMotion.current ? 'auto' : 'smooth',
		block
	});
}
