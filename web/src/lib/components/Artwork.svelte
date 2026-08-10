<!--
	One picture in the site's shared treatment, for the hero collage and for a family graphic.

	It fills the box it is given, so a picture of any size drops in without preparation and none of
	them can size the screen. The ground belongs to that box, which is what lets a collage tile sit on
	block paper and a family graphic on a surface without either being restyled here.

	It fades in when its own image is ready to paint rather than on a timer, which is what stops a
	picture appearing at full opacity the instant it decodes. An entrance sets --arrive-duration and
	--arrive-delay on the box to take that fade over.
-->
<script lang="ts">
	type Props = {
		/** The image to draw, or null while the box is a placeholder. */
		src: string | null;
	};

	let { src }: Props = $props();

	let element = $state<HTMLImageElement>();
	let decoded = $state(false);
	let broken = $state(false);

	/** A box with no image, or one that failed, paints the placeholder and has nothing to wait for. */
	const painting = $derived(src !== null && !broken);
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

<div class="artwork" class:ready class:placeholder={!painting} aria-hidden="true">
	{#if painting}
		<img bind:this={element} {src} alt="" decoding="async" fetchpriority="low" />
	{/if}
</div>

<style>
	/* Fills its box and takes that box's corners, so the picture is clipped to whatever holds it. */
	.artwork {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: clip;
		border-radius: inherit;
		opacity: 0;
	}

	/* An animation rather than a transition, because the class can arrive with the first paint on a
	   placeholder and only later on one still waiting for its picture. */
	.artwork.ready {
		opacity: 1;
		animation: arrive var(--arrive-duration, var(--motion-slow)) var(--ease-in)
			var(--arrive-delay, 0ms) backwards;
	}

	/* Both stops are block family colours, because a picture here is block paper. */
	.placeholder {
		background: linear-gradient(160deg, var(--accent-block), var(--block-muted));
	}

	/* Out of flow, so the picture's own size never reaches the layout around it. */
	img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: var(--art-opacity);
		filter: var(--art-filter);
	}

	@keyframes arrive {
		from {
			opacity: 0;
		}
	}
</style>
