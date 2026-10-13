<script lang="ts">
	type Props = {
		/** A CSS length. Zero must be written as `0px`. */
		bleed?: string;
	};

	let { bleed = 'var(--space-2)' }: Props = $props();

	const STROKES = [
		{
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
					<!-- A near zero-length path with a round cap draws as a dot. -->
					<path d="{at}l0.01 0" style:--speck={size} />
				{/each}
			</g>
		</svg>
	{/each}
</span>

<style>
	.mark {
		position: absolute;
		inset: calc(var(--bleed) * -1);
		display: block;
		container-type: size;
		color: var(--plane-pencil);
		pointer-events: none;
		--width: clamp(1.1px, 4.5cqmin, var(--pencil-width));
	}

	/* Width and height are set because an SVG with only insets keeps the height from its viewBox. */
	.stroke {
		position: absolute;
		inset: 0;
		display: block;
		width: 100%;
		height: 100%;
	}

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
		vector-effect: non-scaling-stroke;
	}

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

	.core .again {
		stroke-width: var(--width);
		opacity: 0.7;
	}

	.specks path {
		stroke-width: calc(var(--width) * var(--speck));
		opacity: 0.55;
	}

	/* Fill mode both keeps the second stroke hidden during its delay. */
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
