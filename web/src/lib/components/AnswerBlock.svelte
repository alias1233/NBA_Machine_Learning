<!--
	The answer the page exists to produce.

	One box, three states. Empty, loading and answered all render the same scaffold at the same size,
	so the page never jumps when a prediction lands.

	The middle of it is a reading, one per answer shape, and each owns its own surface and its own
	reserved space. This holds what every answer has: what was asked, the figure it leads with, and
	the ways out of it.
-->
<script lang="ts">
	import CategoryReading from '$lib/components/CategoryReading.svelte';
	import DistributionReading from '$lib/components/DistributionReading.svelte';
	import { CATEGORY_DECIMALS, expectedValue, figureText, sharePercentages } from '$lib/odds';

	import type { Answer } from '$lib/odds';
	import type { ModelOutput } from '$lib/types';

	type Props = {
		/** The finished answer, or null when nothing has been asked yet. */
		answer: Answer | null;
		/**
		 * The shape the model that was asked answers in, which says which reading to draw and what the
		 * lead figure will be called. Read from the model rather than from the answer, so a block
		 * waiting on one never carries a word from the last one.
		 */
		output: ModelOutput | null;
		/** True while one is being worked out. */
		loading: boolean;
		/** What the model predicts, lowercase. */
		stat: string;
		/** Names the player and the stat, or says what to do before anything has been asked. */
		heading: string;
		/**
		 * Where that heading sits in the page's outline. An answer is a prediction page's second
		 * level, and a third on a page whose own sections are the second.
		 */
		headingLevel?: 2 | 3;
		/**
		 * What the lead figure counts and whose it is, where the model is read from one side of the
		 * game. Empty everywhere else, because the heading already names what was asked about.
		 */
		figureNote?: string;
		/**
		 * What the categories are called for the chosen game, where they name its sides. Null leaves
		 * the model's own words.
		 */
		categoryNames?: string[] | null;
		/** Names the game. Empty before anything has been asked. */
		subheading: string;
		/** The line the address bar already names, if it names one. */
		openOn: number | null;
		/** The family's own page, so a reader can get from the number to how it was reached. */
		aboutHref?: string;
		/**
		 * True where the block stands for an answer rather than being one, which is the About page's
		 * annotated block. It is not a prediction, so the line the reader drags is theirs alone and is
		 * not written into the address bar.
		 */
		example?: boolean;
		/** Whether this answer was asked for with a changed roster. */
		customRoster: boolean;
		/** How many earlier games the answer was built from, or null before there is one. */
		pastGames: number | null;
	};

	let {
		answer,
		output,
		loading,
		stat,
		heading,
		headingLevel = 2,
		figureNote = '',
		categoryNames = null,
		subheading,
		openOn,
		aboutHref,
		example = false,
		customRoster,
		pastGames
	}: Props = $props();

	/** Below this the player has barely played, and an answer built on that little says so. */
	const FEW_PAST_GAMES = 5;

	/** Which reading to draw. Anything the site has no reading for is never offered, so this is safe. */
	const kind = $derived(
		output?.kind === 'category_distribution' ? 'category_distribution' : 'integer_distribution'
	);

	const distribution = $derived(answer?.kind === 'integer_distribution' ? answer.distribution : null);

	// The categories under the words the chosen game gives them, so a win reads as the team's name
	// rather than as the side it plays.
	const categories = $derived.by(() => {
		if (answer?.kind !== 'category_distribution') return null;

		const { names, probabilities } = answer.categories;

		return { names: categoryNames ?? names, probabilities };
	});

	const answered = $derived(answer !== null && !loading);

	/** What the lead figure is called. The model knows this before it has answered. */
	const leadLabel = $derived(
		output?.kind === 'category_distribution'
			? (categoryNames?.[0] ?? output.categories[0])
			: 'Expected'
	);

	// A distribution leads with the value it expects. A set of categories has no value to average, so
	// it leads with the chance of the first one, which is the notable one.
	const leadFigure = $derived.by(() => {
		if (!answered) return '';

		if (distribution) return figureText(distribution, expectedValue(distribution));

		if (categories) {
			return `${sharePercentages(categories.probabilities, CATEGORY_DECIMALS)[0]}%`;
		}

		return '';
	});

	const thin = $derived(answered && pastGames !== null && pastGames < FEW_PAST_GAMES);
</script>

<!-- The one container carrying the accent top edge unhovered, because it is the answer. -->
<section class="block answer">
	<header>
		<!-- The serif role rather than the level's own, so the block reads the same at either. -->
		<svelte:element this={`h${headingLevel}`} class="type-h2">{heading}</svelte:element>
		{#if subheading}
			<p class="muted small">{subheading}</p>
		{/if}

		<!-- Read before the number, because it is about how much stands behind it. -->
		{#if thin}
			<p class="thin small">
				Built from {pastGames}
				{pastGames === 1 ? 'past game' : 'past games'}. An answer from this few is unstable.
			</p>
		{/if}
	</header>

	<!-- data-explain names a part the About page's annotated answer runs a leader line to. -->
	<div class="lead" data-explain="lead">
		<p class="micro muted">{leadLabel}</p>

		<!-- The note comes from the model and the chosen game, so it stands beside the reserved space
		     as well and the block does not change size when the answer lands. -->
		<div class="figure-row">
			{#if answered}
				<p class="figure-lead">{leadFigure}</p>
			{:else}
				<div class="waiting lead-figure"></div>
			{/if}

			{#if figureNote}
				<p class="figure-note">{figureNote}</p>
			{/if}
		</div>
	</div>

	{#if kind === 'category_distribution'}
		<CategoryReading {categories} {loading} />
	{:else}
		<!-- The detailed view covers the page, so it is given the words this block names itself with. -->
		<DistributionReading
			{distribution}
			{loading}
			{stat}
			{openOn}
			{heading}
			{subheading}
			{example}
		/>
	{/if}

	<!-- A changed answer must never look like the default one. -->
	{#if customRoster && answered}
		<p><span class="tag micro">Custom roster</span></p>
	{/if}

	<!-- From the number to how it was reached. A block standing for no model has nowhere to send. -->
	{#if aboutHref}
		<p class="about-link small"><a href={aboutHref}>How this model works</a></p>
	{/if}
</section>

<style>
	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		border-top-color: var(--plane-accent);
	}

	header .type-h2 {
		margin-bottom: var(--space-1);
	}

	/* Full strength beside the muted line above it, so the reader meets it before the figure. */
	.thin {
		margin-top: var(--space-2);
	}

	.lead {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	/* The figure keeps the lead and what it counts follows it on the same baseline, dropping under it
	   where the column is too narrow to hold both. */
	.figure-row {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		column-gap: var(--space-3);
		row-gap: var(--space-1);
	}

	/* The way out of the block is a finger wide, like every other way out on the site. */
	.about-link a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* Reserved space on a block. The page's sunken tone would read as a bright bar here, so a
	   skeleton on a block is drawn in the block's own hairline. It pulses, so the box reads as
	   loading rather than as a finished empty one. */
	.waiting {
		background: var(--hairline-block);
		border-radius: var(--radius);
		animation: pulse var(--loading-pulse) var(--ease-in-out) infinite alternate;
	}

	@keyframes pulse {
		to {
			opacity: 0.4;
		}
	}

	/* Given its width, because it holds nothing to take one from. */
	.waiting.lead-figure {
		width: calc(var(--space-8) * 2);
		max-width: 100%;
		height: var(--type-figure-lead);
	}
</style>
