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
	import { flow } from '$lib/motion';
	import { expectedValue, mostLikelyOutcomes, sharePercentages } from '$lib/odds';

	import type { Answer, AnswerKind } from '$lib/odds';

	type Props = {
		/** The finished answer, or null when nothing has been asked yet. */
		answer: Answer | null;
		/** Which reading to draw, known from the chosen model before an answer lands. */
		kind: AnswerKind;
		/** True while one is being worked out. */
		loading: boolean;
		/** What the model predicts, lowercase. */
		stat: string;
		/** Names the player and the stat, or says what to do before anything has been asked. */
		heading: string;
		/** Names the game. Empty before anything has been asked. */
		subheading: string;
		/** The line the address bar already names, if it names one. */
		openOn: number | null;
		/** The family's own page, so a reader can get from the number to how it was reached. */
		aboutHref: string;
		/** Whether this answer was asked for with a changed roster. */
		customRoster: boolean;
		/** How many earlier games the answer was built from, or null before there is one. */
		pastGames: number | null;
	};

	let {
		answer,
		kind,
		loading,
		stat,
		heading,
		subheading,
		openOn,
		aboutHref,
		customRoster,
		pastGames
	}: Props = $props();

	const MOST_LIKELY = 5;

	/** Below this the player has barely played, and an answer built on that little says so. */
	const FEW_PAST_GAMES = 5;

	const distribution = $derived(answer?.kind === 'integer_distribution' ? answer.distribution : null);
	const categories = $derived(answer?.kind === 'category_distribution' ? answer.categories : null);

	const answered = $derived(answer !== null && !loading);

	// A distribution leads with the value it expects. A set of categories has no value to average, so
	// it leads with the chance of the first one, which is the notable one.
	const lead = $derived.by(() => {
		if (distribution) {
			return {
				label: 'Expected',
				figure: expectedValue(distribution.probabilities, distribution.minimumValue).toFixed(1)
			};
		}

		if (categories) {
			return {
				label: categories.names[0],
				figure: `${sharePercentages(categories.probabilities)[0]}%`
			};
		}

		return { label: 'Expected', figure: '' };
	});

	const likeliest = $derived(
		distribution
			? mostLikelyOutcomes(distribution.probabilities, MOST_LIKELY, distribution.minimumValue)
			: []
	);

	const thin = $derived(answered && pastGames !== null && pastGames < FEW_PAST_GAMES);
</script>

<!-- The one container carrying the accent top edge unhovered, because it is the answer. -->
<section class="block answer">
	<header>
		<h2>{heading}</h2>
		{#if subheading}
			<p class="muted small">{subheading}</p>
		{/if}

		<!-- Read before the number, because it is about how much stands behind it. -->
		{#if thin}
			<p class="thin small" transition:flow>
				Built from {pastGames}
				{pastGames === 1 ? 'past game' : 'past games'}. An answer from this few is unstable.
			</p>
		{/if}
	</header>

	<div class="lead">
		<p class="micro muted">{lead.label}</p>
		{#if answered}
			<p class="figure-lead">{lead.figure}</p>
		{:else}
			<div class="waiting lead-figure"></div>
		{/if}
	</div>

	{#if kind === 'category_distribution'}
		<CategoryReading {categories} {loading} />
	{:else}
		<DistributionReading {distribution} {loading} {stat} {openOn} />
	{/if}

	<!-- Only a run of ordered outcomes has a shortlist worth drawing. Every category is already
	     drawn above, so repeating them here would say the same thing twice. -->
	{#if kind === 'integer_distribution'}
		<div class="likely">
			<h3>Most likely</h3>

			{#if answered}
				<ol class="numeric">
					{#each likeliest as outcome (outcome.value)}
						<li>
							<span>{outcome.value} {stat}</span>
							<span class="muted">{(outcome.probability * 100).toFixed(1)}%</span>
						</li>
					{/each}
				</ol>
			{:else}
				<ol aria-hidden="true">
					{#each Array(MOST_LIKELY) as _, row (row)}
						<li><span class="waiting row"></span></li>
					{/each}
				</ol>
			{/if}
		</div>
	{/if}

	<!-- A changed answer must never look like the default one. -->
	{#if customRoster && answered}
		<p transition:flow><span class="tag micro">Custom roster</span></p>
	{/if}

	<!-- From the number to how it was reached. -->
	<p class="about-link small"><a href={aboutHref}>How this model works</a></p>
</section>

<style>
	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		border-top-color: var(--accent-block);
	}

	header h2 {
		margin-bottom: var(--space-1);
	}

	/* Full strength beside the muted line above it, so the reader meets it before the figure. */
	.thin {
		margin-top: var(--space-2);
	}

	.lead p:first-child {
		margin-bottom: var(--space-2);
	}

	/* The way out of the block is a finger wide, like every other way out on the site. */
	.about-link a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	.likely h3 {
		margin-bottom: var(--space-2);
	}

	.likely ol {
		list-style: none;
		padding: 0;
	}

	.likely li {
		display: flex;
		justify-content: space-between;
		gap: var(--space-3);
		min-height: var(--space-6);
		padding: var(--space-1) 0;
		border-bottom: var(--rule-block);
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

	.waiting.lead-figure {
		height: var(--type-figure-lead);
		max-width: calc(var(--space-8) * 2);
	}

	.waiting.row {
		width: 100%;
		max-width: calc(var(--space-8) * 3);
		height: var(--type-body);
		align-self: center;
	}
</style>
