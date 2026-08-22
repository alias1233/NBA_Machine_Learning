/** Whether a touch ended close enough to where it began to be a tap, not a scroll. */
export function isTap(
	from: { x: number; y: number },
	to: Pick<PointerEvent, 'clientX' | 'clientY'>
): boolean {
	return Math.hypot(to.clientX - from.x, to.clientY - from.y) <= 10;
}
