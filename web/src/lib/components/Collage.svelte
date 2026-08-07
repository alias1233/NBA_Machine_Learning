<!--
	One band of the landing collage.

	The words sit between the two bands, so a tile cannot overlap them at any width or at any point in
	its float. That is R8.7 held by the layout rather than by measurement.
-->
<script lang="ts">
	import { TILES } from '$lib/collage';

	type Props = {
		band: 'top' | 'bottom';
		/** False renders the finished state with no entry animation, which is a return visit. */
		entering: boolean;
	};

	let { band, entering }: Props = $props();

	// Two seconds of spread across the tiles, plus a starting offset each, so no two float together.
	const VARY_SECONDS = 2;
	const OFFSET_SECONDS = 1.7;

	// Inward is towards the centre of the screen: across from the side the tile sits on, and down out
	// of the top band or up out of the bottom one.
	const ACROSS = { start: 1, centre: 0, end: -1 };

	const tiles = $derived(
		TILES.map((tile, index) => ({ ...tile, index })).filter((tile) => tile.band === band)
	);

	// A tile's entry delay, float offset and float duration all come from its index. R7.7 and R7.8.
	const styleOf = (tile: (typeof tiles)[number]) =>
		[
			`--index: ${tile.index}`,
			`--across: ${ACROSS[tile.place]}`,
			`--down: ${band === 'top' ? 1 : -1}`,
			`--ratio: ${tile.ratio}`,
			`--float-vary: ${((tile.index * VARY_SECONDS) / TILES.length).toFixed(2)}s`,
			`--float-offset: -${(tile.index * OFFSET_SECONDS).toFixed(2)}s`
		].join('; ');
</script>

<div class="band {band}" class:entering aria-hidden="true">
	{#each tiles as tile (tile.index)}
		<div class="tile" style={styleOf(tile)}>
			<div class="art" class:placeholder={!tile.image}>
				{#if tile.image}
					<!-- Decorative, so it never blocks first paint and never carries alternative text. A
					     failed image leaves the reserved box empty and moves nothing. R11.4, R11.5. -->
					<img src="/collage/{tile.image}" alt="" decoding="async" fetchpriority="low" />
				{/if}
			</div>
		</div>
	{/each}
</div>

<style>
	.band {
		display: flex;
		justify-content: space-between;
		gap: var(--space-5);
		min-height: 0;
		overflow: clip;
	}

	.top {
		align-items: flex-end;
	}

	.bottom {
		align-items: flex-start;
	}

	/* The reserved box holds the float, so nothing reflows as a tile moves and the clear page the
	   words keep is measured against the tile at the top of its travel. R10.26. */
	.tile {
		flex: 0 1 auto;
		min-width: 0;
		height: 100%;
		padding-top: var(--float-distance);
	}

	.art {
		position: relative;
		height: 100%;
		aspect-ratio: var(--ratio);
		overflow: clip;
		border-radius: var(--radius-lg);
		opacity: var(--collage-opacity);
		animation: float calc(var(--float-cycle) + var(--float-vary)) var(--ease-float) infinite;
		animation-delay: var(--float-offset);
	}

	/* Out of flow, so a picture of any size fills its tile and none of them can size the screen.
	   The collage gives up room before the words do. R6.6. */
	.art img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: var(--collage-filter);
	}

	/* A tile with no image yet paints the duotone gradient across the same rounded box a real one
	   fills, so the collage reads as laid out rather than as a gap waiting to be filled. */
	.placeholder {
		background: linear-gradient(160deg, var(--accent), var(--ink-muted));
	}

	/* Two shorter tiles per band, so the row is a collage rather than a strip of equal blocks. */
	.tile:nth-child(2) {
		height: 76%;
	}

	.tile:nth-child(3) {
		height: 88%;
	}

	.entering .tile {
		animation: arrive var(--motion-entry) var(--ease-in) backwards;
		animation-delay: calc(var(--index) * var(--collage-stagger));
	}

	@keyframes arrive {
		from {
			opacity: 0;
			transform: translate(
				calc(var(--across) * var(--collage-drift) * -1),
				calc(var(--down) * var(--collage-drift) * -1)
			);
		}
	}

	@keyframes float {
		50% {
			translate: 0 calc(var(--float-distance) * -1);
		}
	}
</style>
