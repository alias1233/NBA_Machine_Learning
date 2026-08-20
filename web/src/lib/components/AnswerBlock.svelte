<!--
	The answer the page exists to produce.

	One box, three states. Empty, loading and answered all render the same scaffold at the same size,
	so the page never jumps when a prediction lands.

	The middle of it is a reading, one per answer shape, and each owns its own surface and its own
	reserved space. This holds what every answer has: what was asked, the figure it leads with, and
	the ways out of it.

	Given the whole page, it sets as two: the brief down a rail on the left, and the reading filling
	everything beside it. A distribution is a drawing and every pixel it is given is another outcome
	the reader can tell apart, while what was asked and what it came to are a few short lines that
	gain nothing from a wide measure. In a narrow column, which is the About page's annotated block
	and every phone, the two stack in the order they are read.
-->
<script lang="ts">
	import CategoryReading from '$lib/components/CategoryReading.svelte';
	import DistributionReading from '$lib/components/DistributionReading.svelte';
	import { CATEGORY_DECIMALS, expectedValue, figureText, sharePercentages } from '$lib/odds';
	import { READING_PATH } from '$lib/site';

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
		/**
		 * True where the block stands for an answer rather than being one, which is the About page's
		 * annotated block. It is not a prediction, so the line the reader drags is theirs alone and is
		 * not written into the address bar, and it carries no footer because it already stands in the
		 * section its footer would lead to.
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
	<div class="brief">
		<header>
			<!-- The serif role rather than the level's own, so the block reads the same at either. -->
			<svelte:element this={`h${headingLevel}`} class="type-h2">{heading}</svelte:element>
			{#if subheading}
				<p class="muted small">{subheading}</p>
			{/if}

			<!-- Read before the number, because it is about how much stands behind it. -->
			{#if thin}
				<p class="thin small">
					Built from only {pastGames}
					{pastGames === 1 ? 'earlier game' : 'earlier games'}, so this answer is less reliable than
					usual.
				</p>
			{/if}
		</header>

		<!-- data-explain names a part the About page's annotated answer runs a leader line to. -->
		<div class="lead" data-explain="lead">
			<p class="micro muted">{leadLabel}</p>

			<!-- The note comes from the model and the chosen game, so it stands beside the reserved
			     space as well and the block does not change size when the answer lands. -->
			<div class="figure-row">
				{#if answered}
					<p class="figure-lead" class:printed={!example}>{leadFigure}</p>
				{:else}
					<div class="reserved lead-figure" class:waiting={loading}></div>
				{/if}

				{#if figureNote}
					<p class="figure-note">{figureNote}</p>
				{/if}
			</div>
		</div>

		<!-- A changed answer must never look like the default one, and it says so before the reading
		     rather than after it, the same as the line about how little stands behind one. -->
		{#if customRoster && answered}
			<p><span class="tag micro">Changed roster</span></p>
		{/if}
	</div>

	<div class="reading-area">
		{#if kind === 'category_distribution'}
			<CategoryReading {categories} {loading} />
		{:else}
			<!-- The detailed view covers the page, so it is given the words this block names itself
			     with. -->
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
	</div>

	<!-- The one way out, and what the block is not. A new tab, because everything the reader asked
	     for is in the address bar of the one they are on. Both stand before an answer as well, so the
	     block does not change size when one lands. -->
	{#if !example}
		<footer>
			<p class="small muted">A model's estimate, not betting advice. It is not always right.</p>

			<a class="button button--quiet" href={READING_PATH} target="_blank" rel="noopener">
				How to read this<span class="visually-hidden">, opens in a new tab</span>
			</a>
		</footer>
	{/if}
</section>

<style>
	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		border-top-color: var(--plane-accent);
	}

	.brief {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.reading-area {
		min-width: 0;
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

	/* What the block is not, then the one way out of it. The line reads first because it is about the
	   figure above it. */
	footer {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	/* The last thing the press lays down, so the eye ends on the figure the answer came to. It is
	   held back past the start of the reading beside it, and it is the full impression rather than
	   the reading's strike, because nothing clips it and a headline figure can afford to land. */
	.figure-lead.printed {
		animation: stamp 420ms var(--ease-in) 120ms backwards;
	}

	/* Given its width, because it holds nothing to take one from. The block plane hands it the
	   waiting tone, which on block paper is the block's own hairline. */
	.reserved.lead-figure {
		width: calc(var(--space-8) * 2);
		max-width: 100%;
		height: var(--type-figure-lead);
	}

	/*
	 * Given the page, the block sets as a rail and a drawing. The brief takes the top of the rail and
	 * what the answer is not takes the bottom of it, so the two things a reader needs before and
	 * after the number sit at the two ends of the column they are read in. The reading spans both
	 * rows, and the chart in it is given the height that width asks for.
	 */
	@container answer-column (min-width: 58rem) {
		.answer {
			display: grid;
			grid-template-columns: minmax(0, 19rem) minmax(0, 1fr);
			grid-template-rows: 1fr auto;
			column-gap: var(--space-6);
			row-gap: var(--space-5);
			--chart-height: calc(var(--space-8) * 3.75);
		}

		.reading-area {
			grid-area: 1 / 2 / span 2 / auto;
		}
	}
</style>
