/**
 * Rolling a figure to its new value rather than snapping to it.
 *
 * The duration mirrors `--motion` in `app.css`, which a tween cannot read. Reduced motion drops it
 * to nothing, which stops the animation without stopping the change itself.
 */

import { Tween, prefersReducedMotion } from 'svelte/motion';

const MOTION = 200;

export const rolling = (value: () => number) =>
	Tween.of(value, { duration: () => (prefersReducedMotion.current ? 0 : MOTION) });
