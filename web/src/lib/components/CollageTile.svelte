<!--
	One image in the landing collage. See section 10.10.

	The box is the grid cell the backdrop reserves, and the image is taken out of flow inside it, so
	a picture of any size fills its tile and none of them can size the screen.

	It fades in when its own image is ready to paint rather than on a timer, which is what stops a
	tile appearing at full opacity the instant it decodes. R7.12. Nothing else ever moves it. R7.11.
-->
<script lang="ts">
	type Props = {
		/** A file under `static/collage/`, or null while the tile is a placeholder. */
		image: string | null;
		/** Its place in the order, which is its cell and its share of the entrance stagger. */
		index: number;
		/** True while the once-a-session entrance is playing. R7.10. */
		entering: boolean;
	};

	let { image, index, entering }: Props = $props();

	let element = $state<HTMLImageElement>();
	let decoded = $state(false);
	let broken = $state(false);

	/** A tile with no image, or one that failed, paints the placeholder and has nothing to wait for. */
	const painting = $derived(image !== null && !broken);
	const ready = $derived(!painting || decoded);

	// decode() is what R7.12 means by ready to paint. A load event only says the bytes arrived, and
	// the first paint after one can still lag, which is the pop that rule exists to prevent. It
	// settles whether the image was already cached or is still arriving, so nothing else is needed.
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
	.tile {
		position: relative;
		overflow: clip;
		border-radius: var(--radius-lg);
		opacity: 0;
	}

	/* An animation rather than a transition, because the class can arrive with the first paint on a
	   placeholder tile and only later on one still waiting for its picture. */
	.tile.ready {
		opacity: var(--collage-opacity);
		animation: arrive var(--motion-slow) var(--ease-in) backwards;
	}

	/* The entrance fades each tile in turn, in tile order. R7.10. */
	.tile.entering.ready {
		animation-duration: var(--motion-entry);
		animation-delay: calc(var(--index) * var(--collage-stagger));
	}

	/* Both stops are block family colours, because the backdrop is a block. R8.6, R3.3. */
	.placeholder {
		background: linear-gradient(160deg, var(--accent-block), var(--block-muted));
	}

	img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: var(--collage-filter);
	}

	@keyframes arrive {
		from {
			opacity: 0;
		}
	}
</style>
