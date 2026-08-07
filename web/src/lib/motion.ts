/**
 * Motion a script has to take part in, rather than hand to CSS.
 *
 * `MOTION` mirrors `--motion` in `app.css`, because neither a tween nor a two-phase reveal can read
 * a duration out of a stylesheet. Reduced motion drops a roll to nothing, which stops the animation
 * without stopping the change itself.
 */

import { Tween, prefersReducedMotion } from 'svelte/motion';

/** `--motion`. The roll of R7.2 and the first phase of the answer column reveal in R10.27. */
export const MOTION = 200;

export const rolling = (value: () => number) =>
	Tween.of(value, { duration: () => (prefersReducedMotion.current ? 0 : MOTION) });
