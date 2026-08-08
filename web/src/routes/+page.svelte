<!--
	The home page. A hero about one viewport tall, then the Models section under it.

	The hero is one grid. The backdrop, the tiles and the words are all items on it, so a tile can be
	placed across the backdrop's edge and the words hold a row of their own that no tile reaches. The
	words row sizes itself and the tile rows share what is left, so the collage gives up room before
	the words do.
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import { browser } from '$app/environment';

	import AdSlot from '$lib/components/AdSlot.svelte';
	import CollageTile from '$lib/components/CollageTile.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { TILES } from '$lib/collage';
	import { MODELS_SECTION, familyAboutPath, familyPath } from '$lib/models';
	import { SITE_DESCRIPTION, SITE_NAME } from '$lib/site';

	let { data } = $props();

	const ENTERED = 'hero-entered';

	// The entrance plays once a browser session. The server cannot read sessionStorage, so it renders
	// the entrance and the browser cancels it on a return visit. Reading here rather than in onMount
	// is what keeps a click on the wordmark from showing a frame of it.
	const entering = !browser || sessionStorage.getItem(ENTERED) === null;

	onMount(() => {
		sessionStorage.setItem(ENTERED, '1');
	});
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<meta
		name="description"
		content="The chance of every points, rebounds and assists total for an NBA player in an upcoming game."
	/>
</svelte:head>

<div class="sections">
	<section class="hero">
		<div class="backdrop"></div>

		{#each TILES as image, index (index)}
			<CollageTile {image} {index} {entering} />
		{/each}

		<div class="words" class:entering>
			<h1 class="display">{SITE_NAME}</h1>
			<p>{SITE_DESCRIPTION}</p>

			<div class="actions">
				<a class="button button--lead" href="#{MODELS_SECTION}">Run a prediction</a>
				<a href="/about">How it works</a>
			</div>
		</div>
	</section>

	<section class="page models" id={MODELS_SECTION}>
		<h2>Models</h2>

		{#if data.families.length === 0}
			<Notice>No model is published right now.</Notice>
		{:else}
			{#each data.families as family (family.name)}
				<article class="block family">
					<!-- Reserves what the family graphic will take, so dropping one in shifts nothing. A
					     nested image area inside a block is a surface. -->
					<div class="graphic surface" aria-hidden="true"></div>

					<div class="about">
						<h3>{family.title}</h3>
						<p class="muted">{family.description}</p>

						<!-- A family with nothing trained behind it has nowhere to lead, so it says so
						     instead of offering a page that cannot answer. -->
						<div class="ways">
							{#if family.published}
								<a class="button" href={familyPath(family)}>Predict</a>
								<a class="small" href={familyAboutPath(family)}>How this model works</a>
							{:else}
								<span class="tag micro">Not published yet</span>
							{/if}
						</div>
					</div>
				</article>
			{/each}
		{/if}

		<AdSlot place="homeModels" />
	</section>
</div>

<style>
	/*
	 * Eight rows: three of tiles, the words, three more of tiles, and a strip below the backdrop for
	 * the tiles that hang off it. The outer columns are the inset the backdrop stops short of, so a
	 * tile reaching one crosses an edge, and the padding keeps that overhang on the page rather than
	 * off the side of it.
	 */
	.hero {
		display: grid;
		grid-template-columns: var(--hero-inset) repeat(6, minmax(0, 1fr)) var(--hero-inset);
		grid-template-rows: repeat(3, minmax(0, 1fr)) auto repeat(3, minmax(0, 1fr)) var(--space-7);
		grid-template-areas:
			't1 t1 t1 .  t2 t2 t2 t2'
			't1 t1 t1 .  t2 t2 t2 t2'
			'.  t3 t3 t3 t3 .  .  . '
			'.  w  w  w  w  w  w  . '
			'.  .  t4 t4 t4 t4 .  . '
			't5 t5 t5 .  t6 t6 t6 t6'
			't5 t5 t5 .  t6 t6 t6 t6'
			't5 t5 t5 .  t6 t6 t6 t6';
		gap: var(--collage-gap);
		padding-inline: var(--hero-inset);
		min-height: var(--hero-height);
	}

	/* Sharp edges, and no padding, because what sits on it is placed by the grid rather than by the
	   backdrop. It is declared first, so every tile paints over it. */
	.backdrop {
		grid-area: 2 / 2 / 8 / -2;
		background: var(--block);
	}

	.words {
		grid-area: w;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-4);
		padding: var(--space-3);
		color: var(--block-ink);
		text-align: center;
	}

	/* The words sit on the backdrop, so everything in them comes from the block family. */
	.words a:not(.button) {
		color: var(--accent-block);
	}

	.words .button {
		background: var(--accent-block);
		color: var(--block);
	}

	.words :focus-visible {
		outline-color: var(--accent-block);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: var(--space-5);
		margin-top: var(--space-2);
	}

	.actions a:not(.button) {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* The words arrive once the first tile has landed. */
	.words.entering {
		animation: fade var(--motion-slow) var(--ease-in) var(--motion-entry) backwards;
	}

	@keyframes fade {
		from {
			opacity: 0;
		}
	}

	.models {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.family {
		display: grid;
		gap: var(--space-5);
	}

	/* Square, like a game card, so a family reads in the same language as everything it leads to. It
	   holds the same placeholder as a collage tile until a graphic lands on it. */
	.graphic {
		aspect-ratio: var(--card-ratio);
		background: linear-gradient(160deg, var(--accent-block), var(--block-muted));
	}

	.about {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	/* The ways out sit away from the description rather than under it, so the block reads as a card
	   with something to do at the bottom of it. */
	.ways {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-4);
		margin-top: var(--space-2);
	}

	.ways a:not(.button) {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* Wider tiles, placed further apart, once there is room for the composition to breathe. */
	@media (min-width: 40rem) {
		.hero {
			grid-template-areas:
				't1 t1 .  .  t2 t2 .  . '
				't1 t1 .  .  t2 t2 t3 t3'
				't1 t1 .  .  .  .  t3 t3'
				'.  w  w  w  w  w  w  . '
				'.  .  t4 t4 .  .  t5 t5'
				't6 t6 t4 t4 .  .  t5 t5'
				't6 t6 .  .  .  .  t5 t5'
				't6 t6 .  .  .  .  t5 t5';
		}

		/* The graphic moves beside the words once the block is wide enough to hold both. */
		.family {
			grid-template-columns: calc(var(--space-8) * 2) 1fr;
			align-items: center;
		}
	}
</style>
