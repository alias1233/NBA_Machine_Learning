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
	import Artwork from '$lib/components/Artwork.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { TILES } from '$lib/collage';
	import { familyGraphic } from '$lib/graphics';
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
		content={SITE_DESCRIPTION}
	/>
</svelte:head>

<div class="sections">
	<section class="hero">
		<div class="backdrop"></div>

		<!-- The grid places each tile and the tile carries its own ground, so one crossing the
		     backdrop's edge looks the same on both sides of it. -->
		{#each TILES as image, index (index)}
			<div
				class="tile"
				class:entering
				style="grid-area: t{index + 1}; --arrive-delay: calc({index} * var(--collage-stagger))"
			>
				<Artwork src={image && `/collage/${image}`} />
			</div>
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
		<!-- A family card holds a square and one line, so the listing takes a column of its own and
		     the page tone frames it rather than running under half-empty cards. -->
		<div class="listing">
			<h2>Models</h2>

			{#if data.families.length === 0}
				<Notice>No model is published right now.</Notice>
			{:else}
				{#each data.families as family (family.name)}
					<article class="block family">
						<!-- Reserves what the family graphic takes, so dropping one in shifts nothing. A
						     nested image area inside a block is a surface. -->
						<div class="graphic surface">
							<Artwork src={familyGraphic(family.name)} />
						</div>

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

				<!-- Not a family and nothing to act on, so it is a panel rather than another block. -->
				<div class="panel more">
					<h3>More models</h3>
					<span class="tag micro">Coming soon</span>
				</div>
			{/if}
		</div>

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

	/* The cell a picture fills. It carries the ground, so a tile reads the same on and off the
	   backdrop, and it has sharp edges like the backdrop it is placed on. */
	.tile {
		min-width: 0;
		background: var(--block);
	}

	/* The entrance is the one place a stagger is used, and the delay each tile takes is its own. */
	.tile.entering {
		--arrive-duration: var(--motion-entry);
	}

	/* The words sit on the backdrop, so everything in them comes from the block family, the accent
	   included. */
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
		--plane-accent: var(--accent-block);
		--plane-accent-on: var(--block);
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

	/* Narrower than the page and centred in it. The ad slot below stays on the page width, because
	   it is not part of the listing. */
	.listing {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		width: 100%;
		max-width: var(--family-column);
		margin-inline: auto;
	}

	/* The graphic is beside the words at every width, and the card is what its size is measured
	   against. In one column it takes the title beside it and the rest of the words run the full
	   width underneath, so a narrow card spends its room on the sentence rather than on the square. */
	.family {
		container-type: inline-size;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		grid-template-areas:
			'graphic title'
			'words words'
			'ways ways';
		align-items: center;
		gap: var(--space-4) var(--space-5);
	}

	/* Square, so the picture is read as a mark for the family rather than as a crop of something. The
	   picture fills it, so the surface is the ground and nothing else. */
	.graphic {
		grid-area: graphic;
		width: var(--card-graphic);
		aspect-ratio: var(--graphic-ratio);
		padding: 0;
	}

	/* The words are the card's own rows until there is room to set them as one column. */
	.about {
		display: contents;
	}

	.about h3 {
		grid-area: title;
	}

	.about p {
		grid-area: words;
	}

	.more {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	/* The ways out sit away from the description rather than under it, so the block reads as a card
	   with something to do at the bottom of it. */
	.ways {
		grid-area: ways;
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

	/* Wider tiles, placed further apart, and the family's words set as one column beside its
	   graphic, once there is room for the composition to breathe. */
	@media (min-width: 40rem) {
		.family {
			grid-template-areas: 'graphic about';
		}

		.about {
			grid-area: about;
			display: flex;
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-3);
		}

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
	}
</style>
