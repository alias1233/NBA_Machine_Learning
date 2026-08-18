<!--
	The home page: the hero, then the Models section under it.

	The hero is one screen of printed plate with two sheets of paper lying on it, and it shows the
	day's sample predictions rather than describing what the site does. Nothing there predicts: the
	samples were drawn by a job this morning and are read off a file. See ShowcasePlate.svelte and
	python/src/nba_ml/showcase.py.

	The Models section is the site's index and the one thing the hero leads to. There are three
	families and there will not be many more, so each takes a column of its own, printed on its own
	stock. That is the same ground its prediction page and its About page are printed on, so a reader
	has seen where they are going before they arrive. What is not a family, which today is only the
	line saying more are coming, stands under the row rather than in it.
-->
<script lang="ts">
	import AdSlot from '$lib/components/AdSlot.svelte';
	import Artwork from '$lib/components/Artwork.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import ShowcasePlate from '$lib/components/ShowcasePlate.svelte';
	import { familyGraphic } from '$lib/graphics';
	import { MODELS_SECTION, familyAboutPath, familyPath } from '$lib/models';
	import { SITE_DESCRIPTION, SITE_NAME } from '$lib/site';

	let { data } = $props();
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<meta name="description" content={SITE_DESCRIPTION} />
</svelte:head>

<ShowcasePlate samples={data.samples} heldOver={data.heldOver} answering={data.answering} />

<section class="page models" id={MODELS_SECTION}>
	<!-- Set small on purpose. It names the listing, and the family names under it are what the page
	     is actually offering, so they are what carries the size. -->
	<h2 class="page-title micro muted">Models</h2>

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
				<!-- The family's own stock, which is the ground every page of that family is printed on.
				     One attribute is the whole of what a family colours. -->
				<li class="family plate" data-plate={family.slug}>
					<!-- Reserves what the family graphic takes, so dropping one in shifts nothing. -->
					<div class="graphic">
						<Artwork src={familyGraphic(family.name)} />
					</div>

					<div class="said">
						<h3 class="plate-display">{family.title}</h3>
						<p class="words">{family.description}</p>
					</div>

					<!-- A family with nothing trained behind it has nowhere to lead, so it says so instead
					     of offering a page that cannot answer. -->
					<div class="ways">
						{#if family.published}
							<a class="button" href={familyPath(family)}>Run a prediction</a>
							<a class="small text-link" href={familyAboutPath(family)}>How these models work</a>
						{:else}
							<span class="tag micro">Not published yet</span>
						{/if}
					</div>
				</li>
			{/each}
		</ul>

		<!-- Not a family and nothing to act on, so it stands under the row as one printed line rather
		     than as a fourth column with empty stock. -->
		<p class="more muted">More models <span class="tag micro">Coming soon</span></p>
	{/if}

	<AdSlot place="homeModels" />
</section>

<style>
	.models {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		padding-block-start: var(--space-7);
	}

	/*
	 * The families as columns of printed stock, meeting along their edges so the row reads as one
	 * sheet run in three inks rather than as three cards laid out with space between them.
	 *
	 * How many fit across is measured against the page, so a family added later takes its place
	 * without a number here changing.
	 */
	.families {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.family {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		padding: var(--space-5);
	}

	/* Square, because everything printed on this site is. */
	.graphic {
		aspect-ratio: var(--graphic-ratio);
		background: var(--plate-deep);
	}

	.said {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	/* Stamped, at the size a column holds rather than the size a whole band does. The plate's own
	   lettering, because the site's serif never appears on printed stock. */
	.family h3 {
		font-size: var(--type-h2);
	}

	.words {
		color: var(--plate-ink-muted);
	}

	/* Held at the foot of the column, so the three ways in line up across the row however long the
	   names and the lines above them run. */
	.ways {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-4);
		margin-block-start: auto;
	}

	/* A way to read about a family is printed in the one ink rather than in the spot colour, which
	   belongs to the action rather than to a link beside it. It also clears 4.5:1 on every stock,
	   which the spot ink does not. */
	.ways .text-link {
		--plane-accent: var(--plate-ink);
	}

	.more {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
		padding-block-start: var(--space-3);
		border-top: var(--rule-panel);
	}

	@media (min-width: 48rem) {
		.families {
			grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		}
	}
</style>
