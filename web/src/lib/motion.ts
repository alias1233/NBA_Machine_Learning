/**
 * Motion a script has to take part in, rather than hand to CSS.
 *
 * These mirror `app.css`, because neither a tween, a two-phase reveal nor a timer can read a
 * duration out of a stylesheet. Reduced motion drops a roll to nothing, which stops the animation
 * without stopping the change itself.
 */

import { Tween, prefersReducedMotion } from 'svelte/motion';

/** `--motion`. A rolling figure, and the first phase of the answer column reveal. */
export const MOTION = 200;

/** `--motion-slow`. The chart drawing in, and the column widening. */
export const MOTION_SLOW = 320;

export const rolling = (value: () => number) =>
	Tween.of(value, { duration: () => (prefersReducedMotion.current ? 0 : MOTION) });
