<!--
	The reader's own mark: a wet-erase X over the one thing they picked.

	Two strokes, neither of them straight, one overshooting its corner and one stopping short. That
	unevenness is the whole difference between a drawn mark and a printed one, and it is what says the
	mark belongs to the reader rather than to the model.

	It arrives as if sprayed. The mask opens outwards from the middle, so the crossing lands first and
	the four ends reach their corners after it, and a haze of the same shape sits behind the strokes
	as overspray. Nothing about the reveal is measured along the path, so a mark stretched to a wide
	box arrives exactly the way one stretched to a tall box does.

	It hangs outside the thing it marks, so whatever holds it is positioned and gives it room. Its ink
	comes from the plane it lands on, which is what keeps a mark readable on bone stock and on a blue
	plate alike.
-->
<script lang="ts">
	type Props = {
		/** How far outside the marked box the mark hangs, as a length. */
		bleed?: string;
	};

	let { bleed = 'var(--space-2)' }: Props = $props();

	/** Down to the right, overshooting the corner. */
	const FALL = 'M8 7C25 24 43 41 61 59 71 69 80 78 95 94';
	/** Down to the left, stopping short of it. */
	const RISE = 'M93 9C76 27 58 45 41 63 31 73 22 82 11 91';
</script>

<svg class="mark" style:--bleed={bleed} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
	<g class="haze">
		<path d={FALL} />
		<path d={RISE} />
	</g>
	<g class="stroke">
		<path d={FALL} />
		<path d={RISE} />
	</g>
</svg>

<style>
	/* Sized explicitly rather than by inset. An SVG has an intrinsic size of its own, and left to it
	   the mark is drawn at that size and hangs across whatever sits beside the thing it marks. */
	.mark {
		position: absolute;
		top: calc(var(--bleed) * -1);
		left: calc(var(--bleed) * -1);
		display: block;
		width: calc(100% + var(--bleed) * 2);
		height: calc(100% + var(--bleed) * 2);
		color: var(--plane-pencil);
		pointer-events: none;
		/* The reveal. It opens from the middle of the mark outwards, so the crossing is there before
		   the ends are. At rest --spray is past the far corner and the mask holds nothing back. */
		mask-image: radial-gradient(
			circle at 50% 50%,
			#000 0%,
			#000 var(--spray),
			transparent calc(var(--spray) + 18%)
		);
	}

	.mark path {
		fill: none;
		stroke: currentColor;
		stroke-linecap: round;
		stroke-width: calc(var(--pencil-width) * 1.5);
		/* The stroke keeps its weight whatever box the mark is stretched to. */
		vector-effect: non-scaling-stroke;
	}

	/* Overspray: the same two strokes laid down wider and softer, which is what a sprayed edge is. */
	.haze path {
		stroke-width: calc(var(--pencil-width) * 4);
		opacity: 0.3;
		filter: blur(3px);
	}

	@media (prefers-reduced-motion: no-preference) {
		.mark {
			animation: spray var(--motion-slow) var(--ease-in);
		}
	}

	@keyframes spray {
		from {
			--spray: 0%;
			opacity: 0;
			filter: blur(5px);
		}

		40% {
			opacity: 1;
		}

		to {
			--spray: 100%;
			opacity: 1;
			filter: blur(0);
		}
	}
</style>
