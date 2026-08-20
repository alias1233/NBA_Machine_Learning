<!--
	The reader's own mark: a wet-erase X over the one thing they picked.

	Two strokes, drawn one at a time and in the order a hand draws them: down to the left first, then
	down to the right across it. Neither runs straight, one overshoots its corner and one stops short,
	and each is laid twice, the way a hand goes back over a line it is not happy with. That wavering
	and that order are the whole difference between a drawn mark and a printed one.

	Each stroke sprays rather than draws. It is built the way a sprayed line is: a wide soft cloud, a
	denser halo inside it, and a hard core down the middle, with specks carried off the line where the
	can spat and where the hand came down and lifted. The ink lands from the corner the stroke starts
	at and runs along it, and nothing about that reveal is measured along the path, so a mark stretched
	to a wide box arrives exactly the way one stretched to a tall box does.

	It hangs outside the thing it marks, so whatever holds it is positioned and gives it room. Its ink
	comes from the plane it lands on, which is what keeps a mark readable on bone stock and on a blue
	plate alike.
-->
<script lang="ts">
	type Props = {
		/** How far outside the marked box the mark hangs. A CSS length, so a zero is written `0px`. */
		bleed?: string;
	};

	let { bleed = 'var(--space-2)' }: Props = $props();

	/**
	 * The two strokes, each as the line the hand meant, the line it left going back over it, and the
	 * specks that carried off both.
	 *
	 * Held here rather than in the markup because the pair are the same gesture twice and reading them
	 * side by side is what says which one overshoots and which one stops short. Every path wanders to
	 * either side of its own diagonal rather than bowing off it once, because a bow reads as a curve
	 * that was meant and a wander reads as a hand.
	 */
	const STROKES = [
		{
			/** Down to the left, starting past its corner and stopping short of the far one. */
			name: 'rise',
			core: 'M96 3C89 13 82 22 74 31 66 40 54 44 46 52 38 60 33 73 24 80 17 86 11 92 3 99',
			again: 'M91 10C84 19 76 26 69 36 62 46 52 52 44 60 36 68 30 77 21 85',
			specks: [
				['M98 1', 2.4],
				['M86 12', 1.2],
				['M79 27', 1],
				['M57 44', 1.4],
				['M33 71', 1.1],
				['M14 89', 1.5],
				['M2 100', 2.2]
			]
		},
		{
			/** Down to the right, starting inside its corner and carrying past the far one. */
			name: 'fall',
			core: 'M4 4C13 12 24 18 32 27 40 36 42 51 51 59 60 67 71 75 80 85 86 91 92 94 99 99',
			again: 'M11 10C19 18 29 25 36 34 43 43 48 55 56 63 64 71 73 79 89 91',
			specks: [
				['M2 2', 2.2],
				['M16 11', 1.1],
				['M28 33', 1.3],
				['M46 50', 0.9],
				['M63 62', 1.2],
				['M84 80', 1.4],
				['M99 100', 2.4]
			]
		}
	] as const;
</script>

<span class="mark" style:--bleed={bleed} aria-hidden="true">
	{#each STROKES as stroke (stroke.name)}
		<!-- One stroke to a sheet, because each is masked from its own starting corner and the two are
		     laid one after the other. -->
		<svg class="stroke {stroke.name}" viewBox="0 0 100 100" preserveAspectRatio="none">
			<g class="cloud">
				<path d={stroke.core} />
				<path d={stroke.again} />
			</g>
			<g class="halo">
				<path d={stroke.core} />
				<path d={stroke.again} />
			</g>
			<g class="core">
				<path d={stroke.core} />
				<path class="again" d={stroke.again} />
			</g>
			<g class="specks">
				{#each stroke.specks as [at, size] (at)}
					<!-- A speck, not a line: a subpath with nowhere to go and a round cap. Its stroke does
					     not scale, so a speck stays round however the box is stretched. -->
					<path d="{at}l0.01 0" style:--speck={size} />
				{/each}
			</g>
		</svg>
	{/each}
</span>

<style>
	/*
	 * Held out from every edge of the thing it marks by its bleed, so the mark is the size of that box
	 * plus the overhang and never an intrinsic size of its own.
	 *
	 * How heavy the pencil is measured against the mark rather than against the page, because it is a
	 * size that belongs to this component: the same X is drawn across a whole sample on the hero and
	 * into the corner of a playing card, and one weight cannot serve both. --pencil-width is the
	 * heaviest it is ever drawn, and the floor is the finest a stroke still reads at.
	 */
	.mark {
		position: absolute;
		inset: calc(var(--bleed) * -1);
		display: block;
		container-type: size;
		color: var(--plane-pencil);
		pointer-events: none;
		--width: clamp(1.1px, 4.5cqmin, var(--pencil-width));
	}

	/* Stretched to the mark's box in both directions. An SVG given only insets keeps the height its own
	   viewBox asks for, so a mark drawn across a box wider than it is tall would be laid out square and
	   hang out of the bottom of it. */
	.stroke {
		position: absolute;
		inset: 0;
		display: block;
		width: 100%;
		height: 100%;
	}

	/*
	 * The ink landing along the stroke. The mask runs from the corner the stroke starts at to the one
	 * it ends at, with a soft leading edge, so the run of ink has a wet end rather than a cut one. At
	 * rest --laid is past the far corner and the mask holds nothing back.
	 */
	.rise {
		mask-image: linear-gradient(
			to bottom left,
			#000 0%,
			#000 var(--laid),
			transparent calc(var(--laid) + 16%)
		);
	}

	.fall {
		mask-image: linear-gradient(
			to bottom right,
			#000 0%,
			#000 var(--laid),
			transparent calc(var(--laid) + 16%)
		);
	}

	.stroke path {
		fill: none;
		stroke: currentColor;
		stroke-linecap: round;
		/* Every stroke keeps its weight whatever box the mark is stretched to. */
		vector-effect: non-scaling-stroke;
	}

	/* The three layers a sprayed line is made of, outside in: the cloud is where the ink drifted, the
	   halo is where it settled, and the core is where the can was actually pointed. Each is a multiple
	   of the one weight, so a mark drawn small is the same mark and not a heavier one. */
	.cloud path {
		stroke-width: calc(var(--width) * 5);
		opacity: 0.12;
		filter: blur(calc(var(--width) * 2.2));
	}

	.halo path {
		stroke-width: calc(var(--width) * 2.4);
		opacity: 0.26;
		filter: blur(calc(var(--width) * 0.8));
	}

	.core path {
		stroke-width: calc(var(--width) * 1.4);
	}

	/* The second pass over the same line, thinner and short of full strength, which is what makes one
	   stroke read as one gesture rather than as one path. */
	.core .again {
		stroke-width: var(--width);
		opacity: 0.7;
	}

	/* Where the can spat, and where the hand came down and lifted. */
	.specks path {
		stroke-width: calc(var(--width) * var(--speck));
		opacity: 0.55;
	}

	/*
	 * Laid one at a time, in the order a hand draws an X. The second stroke holds at nothing through
	 * the first one's run, which is what the backwards fill is for, so the two are read as one gesture
	 * after another rather than as one mark switching on.
	 */
	@media (prefers-reduced-motion: no-preference) {
		.stroke {
			animation: lay var(--pencil-stroke) var(--ease-in) both;
		}

		.fall {
			animation-delay: var(--pencil-stagger);
		}
	}

	@keyframes lay {
		from {
			--laid: 0%;
			opacity: 0;
		}

		12% {
			opacity: 1;
		}

		to {
			--laid: 100%;
			opacity: 1;
		}
	}
</style>
