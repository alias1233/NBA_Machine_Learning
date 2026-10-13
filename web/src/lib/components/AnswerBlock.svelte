<script lang="ts">
	import CategoryReading from '$lib/components/CategoryReading.svelte';
	import DistributionReading from '$lib/components/DistributionReading.svelte';
	import { CATEGORY_DECIMALS, expectedValue, figureText, sharePercentages } from '$lib/odds';
	import { READING_PATH } from '$lib/site';

	import type { Answer } from '$lib/odds';
	import type { ModelOutput } from '$lib/types';

	type Props = {
		/** The prediction result, or null if nothing has been requested yet. */
		answer: Answer | null;
		/** Output format of the requested model. */
		output: ModelOutput | null;
		loading: boolean;
		/** Name of the predicted stat, in lowercase. */
		stat: string;
		heading: string;
		headingLevel?: 2 | 3;
		/** Describes the main number and the team it is for. */
		figureNote?: string;
		categoryNames?: string[] | null;
		subheading: string;
		/** Line from the URL, if there is one. */
		openOn: number | null;
		/** True when the block is a static example and not a real prediction. */
		example?: boolean;
		customRoster: boolean;
		/** Number of past games the prediction used, or null before there is one. */
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

	const FEW_PAST_GAMES = 5;

	/** Type of result to show. */
	const kind = $derived(
		output?.kind === 'category_distribution' ? 'category_distribution' : 'integer_distribution'
	);

	const distribution = $derived(answer?.kind === 'integer_distribution' ? answer.distribution : null);

	const categories = $derived.by(() => {
		if (answer?.kind !== 'category_distribution') return null;

		const { names, probabilities } = answer.categories;

		return { names: categoryNames ?? names, probabilities };
	});

	const answered = $derived(answer !== null && !loading);

	const leadLabel = $derived(
		output?.kind === 'category_distribution'
			? (categoryNames?.[0] ?? output.categories[0])
			: 'Expected'
	);

	const leadFigure = $derived.by(() => {
		if (!answered) return '';

		if (distribution) return figureText(distribution, expectedValue(distribution));

		if (categories) {
			return `${sharePercentages(categories.probabilities, CATEGORY_DECIMALS)[0]}%`;
		}

		return '';
	});

	const thin = $derived(answered && pastGames !== null && pastGames < FEW_PAST_GAMES);

	// svelte-ignore state_referenced_locally
	let seenAnswer = $state.raw<Answer | null>(answer);
	let drawBars = $state(false);

	$effect(() => {
		const next = answer;

		if (loading || next === null || next === seenAnswer) return;

		drawBars = true;
		seenAnswer = next;
	});
</script>

<section class="block answer">
	<div class="brief">
		<header>
			<svelte:element this={`h${headingLevel}`} class="type-h2">{heading}</svelte:element>
			{#if subheading}
				<p class="muted small">{subheading}</p>
			{/if}

			{#if thin}
				<p class="thin small">
					Built from only {pastGames}
					{pastGames === 1 ? 'earlier game' : 'earlier games'}, so this answer is less reliable than
					usual.
				</p>
			{/if}
		</header>

		<!-- data-explain marks a part that the About page's annotated example points to. -->
		<div class="lead" data-explain="lead">
			<p class="micro muted">{leadLabel}</p>

			<div class="figure-row">
				{#if answered}
					<p class="figure-lead">{leadFigure}</p>
				{:else}
					<div class="reserved lead-figure" class:waiting={loading}></div>
				{/if}

				{#if figureNote}
					<p class="figure-note">{figureNote}</p>
				{/if}
			</div>
		</div>

		{#if customRoster && answered}
			<p><span class="tag micro">Changed roster</span></p>
		{/if}
	</div>

	<div class="reading-area">
		{#if kind === 'category_distribution'}
			<CategoryReading {categories} {loading} animateBars={drawBars} />
		{:else}
			<DistributionReading
				{distribution}
				{loading}
				{stat}
				{openOn}
				{heading}
				{subheading}
				{example}
				animateBars={drawBars}
			/>
		{/if}
	</div>

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
		border-radius: 0;
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

	.thin {
		margin-top: var(--space-2);
	}

	.lead {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.figure-row {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		column-gap: var(--space-3);
		row-gap: var(--space-1);
	}

	footer {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.reserved.lead-figure {
		width: calc(var(--space-8) * 2);
		max-width: 100%;
		height: var(--type-figure-lead);
	}

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
