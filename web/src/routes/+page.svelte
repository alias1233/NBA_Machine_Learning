<!--
	The home page: the hero, then the Models section under it.

	The hero is one screen of printed plate with two sheets of paper lying on it, and it shows the
	day's sample predictions rather than describing what the site does. Nothing there predicts: the
	samples were drawn by a job this morning and are read off a file. See ShowcasePlate.svelte and
	python/src/nba_ml/showcase.py.

	The Models section is the site's index and the one thing the hero leads to. It reads directly on
	the reader's own page. Each family is held by its own block-paper frame, so the page stays visible
	between the three choices and the frames themselves are the objects in the section.

	A wide landscape device holds the three frames side by side at the same height. A smaller screen
	lets the grid break into fewer columns, so every family remains readable and usable.

	A family is not a picture, it is the models in it, so each frame prints them by name with what
	each one answers. See FamilySheet.svelte.

	What is not a family, which today is only the line saying more are coming, stands below the frames.
-->
<script lang="ts">
	import AdSlot from '$lib/components/AdSlot.svelte';
	import FamilySheet from '$lib/components/FamilySheet.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PageMetadata from '$lib/components/PageMetadata.svelte';
	import ShowcasePlate from '$lib/components/ShowcasePlate.svelte';
	import { MODELS_PATH, MODELS_SECTION } from '$lib/models';
	import { webApplicationSchema } from '$lib/seo';
	import { PRIVATE_SITE_DESCRIPTION } from '$lib/site';
	import { isTap } from '$lib/touch';

	let { data } = $props();

	let activeTouchFamily = $state<string | null>(null);
	let touchStartedOutside: { id: number; x: number; y: number } | null = null;

	function touchFamily(event: PointerEvent) {
		if (event.pointerType !== 'touch') return;

		const section = document.getElementById(MODELS_SECTION);
		const family =
			section?.contains(event.target as Node) && event.target instanceof Element
				? event.target.closest<HTMLElement>('[data-family]')
				: null;

		if (family?.dataset.family) {
			activeTouchFamily = family.dataset.family;
			touchStartedOutside = null;
			return;
		}

		touchStartedOutside = { id: event.pointerId, x: event.clientX, y: event.clientY };
	}

	function releaseTouchFamily(event: PointerEvent) {
		if (event.pointerType !== 'touch' || touchStartedOutside?.id !== event.pointerId) return;

		if (isTap(touchStartedOutside, event)) activeTouchFamily = null;

		touchStartedOutside = null;
	}
</script>

<PageMetadata description={PRIVATE_SITE_DESCRIPTION} path="/" schema={webApplicationSchema()} />

<ShowcasePlate samples={data.samples} heldOver={data.heldOver} answering={data.answering} />

<svelte:window
	onpointerdown={touchFamily}
	onpointerup={releaseTouchFamily}
	onpointercancel={() => (touchStartedOutside = null)}
/>

<section class="models lands-flush" id={MODELS_SECTION}>
	<a class="models-tab" href={MODELS_PATH}>Models</a>

	<div class="page inside">
		<div class="head">
			<h2 class="page-title type-h1">Models</h2>
		</div>

		<!-- A dead service leaves this list empty too, and telling a reader nothing is published would
		     name the wrong cause. The footer says the same thing at the same moment. -->
		{#if data.families.length === 0}
			{#if data.health}
				<Notice>No model is published yet.</Notice>
			{:else}
				<!-- Names the cause but not the recovery. The hero above and the footer below both already
				     tell the reader to come back, and three of that on one screen is two too many. It still
				     stands alone for somebody who arrived straight at this section. -->
				<Notice>No model can be listed while the prediction service is not answering.</Notice>
			{/if}
		{:else}
			<ul class="families">
				{#each data.families as family (family.name)}
					<FamilySheet {family} touchActive={activeTouchFamily === family.name} />
				{/each}
			</ul>
		{/if}

		<p class="more muted">More models <span class="tag micro">Coming soon</span></p>

		<AdSlot place="homeModels" />
	</div>
</section>

<style>
	.models {
		position: relative;
		display: flex;
		flex-direction: column;
		padding-block: var(--space-6) var(--space-5);
		background: var(--page);
	}

	/* The listing's first piece of paper. Its page edge stays square while the far edge takes the
	   fold of a folder tab. */
	.models-tab {
		position: absolute;
		inset-block-end: 100%;
		inset-inline-start: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		min-block-size: var(--tap-target);
		inline-size: max(calc(var(--tap-target) * 4), 20vw);
		padding-inline: var(--space-5);
		background: var(--page);
		border: var(--rule);
		border-block-end: 0;
		clip-path: polygon(0 0, calc(100% - var(--space-3)) 0, 100% 100%, 0 100%);
		color: var(--ink);
		font-size: var(--type-small);
		font-weight: 700;
		text-decoration: none;
		white-space: nowrap;
		transition: color var(--motion-fast) var(--ease-in);
	}

	.models-tab:hover {
		color: var(--plane-accent);
	}

	.inside {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: var(--space-5);
	}

	.families {
		display: grid;
		flex: 1;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
		grid-auto-rows: minmax(var(--models-frame-min-height), auto);
		gap: var(--space-5);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.more {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
	}

	/*
	 * Landscape, the whole section is one screen, starting at the top edge it lands on. The
	 * frames take whatever the heading and the line under it leave, so every family stays in sight
	 * and every way into it can be pressed without a scroll.
	 *
	 * Orientation rather than width, because what decides this is whether the device has height to
	 * spend or scroll to save, which is the same question the stacked bricks answer the other way.
	 * The smallest screen is what it is measured against, so a phone's browser bars coming back
	 * cannot push the foot of the board off the bottom.
	 */
	@media (min-width: 64rem) and (orientation: landscape) {
		.models {
			/* Held closer to the hero than a section on paper usually is, because here the room above
			   the heading is room off the board, and the board is what has to fit. */
			padding-block: var(--space-5);
			/* A whole screen, because .lands-flush puts the section's top edge on the top of it. */
			min-height: 100svh;
		}

		.families {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			grid-template-rows: minmax(0, 1fr);
			grid-auto-rows: minmax(0, 1fr);
			min-height: 0;
			padding-block-end: calc(var(--models-frame-stagger) * 2);
		}

		:global(.families > .family:nth-child(2)) {
			translate: 0 var(--models-frame-stagger);
		}

		:global(.families > .family:nth-child(3)) {
			translate: 0 calc(var(--models-frame-stagger) * 2);
		}
	}
</style>
