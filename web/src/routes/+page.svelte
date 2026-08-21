<!--
	The home page: the hero, then the Models section under it.

	The hero is one screen of printed plate with two sheets of paper lying on it, and it shows the
	day's sample predictions rather than describing what the site does. Nothing there predicts: the
	samples were drawn by a job this morning and are read off a file. See ShowcasePlate.svelte and
	python/src/nba_ml/showcase.py.

	The Models section is the site's index and the one thing the hero leads to. It reads on the
	reader's own page, headed like every other page on the site, with one board of block paper laid
	across it holding the families. The board is the object here, which is what a block is for: the
	page is where the reader is and the board is the thing set into it.

	It is one screen on a landscape device, and a link to it lands on its own top edge, so the
	heading, the whole board and the line under it are all in sight at once and every way into a
	family can be pressed without a scroll. Portrait, the families stack as bricks and the section
	runs as long as they need, because there a screen cannot hold three families and be read.

	A family is not a picture, it is the models in it, so each sheet prints them by name with what
	each one answers. See FamilySheet.svelte.

	What is not a family, which today is only the line saying more are coming, stands under the board
	rather than on it.
-->
<script lang="ts">
	import AdSlot from '$lib/components/AdSlot.svelte';
	import FamilySheet from '$lib/components/FamilySheet.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import ShowcasePlate from '$lib/components/ShowcasePlate.svelte';
	import { MODELS_PATH, MODELS_SECTION } from '$lib/models';
	import { SITE_DESCRIPTION, SITE_NAME } from '$lib/site';

	let { data } = $props();
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<meta name="description" content={SITE_DESCRIPTION} />
</svelte:head>

<ShowcasePlate samples={data.samples} heldOver={data.heldOver} answering={data.answering} />

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
			<div class="board">
				<ul class="families">
					{#each data.families as family, position (family.name)}
						<FamilySheet {family} {position} />
					{/each}
				</ul>
			</div>
		{/if}

		<p class="more muted">More models <span class="tag micro">Coming soon</span></p>

		<AdSlot place="homeModels" />
	</div>
</section>

<style>
	/*
	 * The section is the reader's own page, which is what every screen under a band is. Only the board
	 * inside it is block paper, because the families are an object set into the page rather than a
	 * field of it.
	 */
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

	.board {
		display: flex;
		flex-direction: column;
	}

	/* The families form one press composition. The first sheet anchors the run and the others bind to
	   its edge, which makes the page read as a single object rather than three equal cards. */
	.families {
		display: grid;
		flex: 1;
		gap: var(--models-board-gap);
		margin: 0;
		padding: var(--models-board-inset);
		background: var(--models-board-ground);
		box-shadow: var(--models-board-shadow);
		list-style: none;
		isolation: isolate;
	}

	.more {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
	}

	/*
	 * Landscape, the whole section is one screen, starting at the top edge it lands on. The
	 * board takes whatever the heading and the line under it leave, so both its edges are in sight
	 * and the way into every family can be pressed without a scroll.
	 *
	 * Orientation rather than width, because what decides this is whether the device has height to
	 * spend or scroll to save, which is the same question the stacked bricks answer the other way.
	 * The smallest screen is what it is measured against, so a phone's browser bars coming back
	 * cannot push the foot of the board off the bottom.
	 */
	@media (orientation: landscape) {
		.models {
			/* Held closer to the hero than a section on paper usually is, because here the room above
			   the heading is room off the board, and the board is what has to fit. */
			padding-block: var(--space-5);
			/* A whole screen, because .lands-flush puts the section's top edge on the top of it. */
			min-height: 100svh;
		}

		.board {
			flex: 1;
			min-height: 0;
		}

		.families {
			grid-template-columns: minmax(0, var(--models-lead-span)) minmax(
				var(--models-support-min),
				1fr
			);
			grid-template-rows: repeat(2, minmax(0, 1fr));
		}
	}
</style>
