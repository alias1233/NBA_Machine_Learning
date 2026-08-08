<!--
	One image in the hero collage.

	The box is the grid cell the hero reserves, and the image is taken out of flow inside it, so a
	picture of any size fills its tile and none of them can size the screen. The tile carries the
	block tone as its own ground, so one placed across the backdrop's edge looks the same on both
	sides of it.

	It fades in when its own image is ready to paint rather than on a timer, which is what stops a
	tile appearing at full opacity the instant it decodes. Nothing else ever moves it.
-->
<script lang="ts">
	type Props = {
		/** A file under `static/collage/`, or null while the tile is a placeholder. */
		image: string | null;
		/** Its place in the order, which is its cell and its share of the entrance stagger. */
		index: number;
		/** True while the once-a-session entrance is playing. */
		entering: boolean;
	};

	let { image, index, entering }: Props = $props();

	let element = $state<HTMLImageElement>();
	let decoded = $state(false);
	let broken = $state(false);

	/** A tile with no image, or one that failed, paints the placeholder and has nothing to wait for. */
	const painting = $derived(image !== null && !broken);
	const ready = $derived(!painting || decoded);

	// decode() is what ready to paint means. A load event only says the bytes arrived, and the first
	// paint after one can still lag, which is the pop this exists to prevent. It settles whether the
	// image was already cached or is still arriving, so nothing else is needed.
	$effect(() => {
		if (!element) return;

		let live = true;

		element
			.decode()
			.then(() => live && (decoded = true))
			.catch(() => live && (broken = true));

		return () => {
			live = false;
		};
	});
</script>

<div
	class="tile"
	class:ready
	class:entering
	class:placeholder={!painting}
	style="grid-area: t{index + 1}; --index: {index}"
	aria-hidden="true"
>
	{#if painting}
		<img bind:this={element} src="/collage/{image}" alt="" decoding="async" fetchpriority="low" />
	{/if}
</div>

<style>
	/* Sharp edges, like the backdrop it is placed on. */
	.tile {
		position: relative;
		overflow: clip;
		background: var(--block);
		opacity: 0;
	}

	/* An animation rather than a transition, because the class can arrive with the first paint on a
	   placeholder tile and only later on one still waiting for its picture. */
	.tile.ready {
		opacity: 1;
		animation: arrive var(--motion-slow) var(--ease-in) backwards;
	}

	/* The entrance fades each tile in turn, in tile order. */
	.tile.entering.ready {
		animation-duration: var(--motion-entry);
		animation-delay: calc(var(--index) * var(--collage-stagger));
	}

	/* Both stops are block family colours, because a tile is block paper. */
	.placeholder {
		background: linear-gradient(160deg, var(--accent-block), var(--block-muted));
	}

	img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: var(--collage-opacity);
		filter: var(--collage-filter);
	}

	@keyframes arrive {
		from {
			opacity: 0;
		}
	}
</style>
