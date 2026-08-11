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
	import { CATEGORY_DECIMALS, expectedValue, sharePercentages } from '$lib/odds';

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
		/**
		 * A second figure beside the lead one, for an answer that carries a reading its shape alone
		 * does not give. Null where it carries none, which is most of them.
		 *
		 * The label is named by the model, so it stands while an answer is worked out. The figure is
		 * read off the answer, so it is empty until there is one.
		 */
		second?: { label: string; figure: string } | null;
	};

	let {
		answer,
		output,
		loading,
		stat,
		heading,
		subheading,
		openOn,
		aboutHref,
		customRoster,
		pastGames,
		second = null
	}: Props = $props();

	/** Below this the player has barely played, and an answer built on that little says so. */
	const FEW_PAST_GAMES = 5;

	/** Which reading to draw. Anything the site has no reading for is never offered, so this is safe. */
	const kind = $derived(
		output?.kind === 'category_distribution' ? 'category_distribution' : 'integer_distribution'
	);

	const distribution = $derived(answer?.kind === 'integer_distribution' ? answer.distribution : null);
	const categories = $derived(answer?.kind === 'category_distribution' ? answer.categories : null);

	const answered = $derived(answer !== null && !loading);

	/** What the lead figure is called. The model knows this before it has answered. */
	const leadLabel = $derived(
		output?.kind === 'category_distribution' ? output.categories[0] : 'Expected'
	);

	// A distribution leads with the value it expects. A set of categories has no value to average, so
	// it leads with the chance of the first one, which is the notable one.
	const leadFigure = $derived.by(() => {
		if (!answered) return '';

		if (distribution) return expectedValue(distribution).toFixed(1);

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
		<h2>{heading}</h2>
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

	<div class="lead">
		<div>
			<p class="micro muted">{leadLabel}</p>
			{#if answered}
				<p class="figure-lead">{leadFigure}</p>
			{:else}
				<div class="waiting lead-figure"></div>
			{/if}
		</div>

		{#if second}
			<div>
				<p class="micro muted">{second.label}</p>
				{#if answered}
					<p class="figure-lead">{second.figure}</p>
				{:else}
					<div class="waiting lead-figure"></div>
				{/if}
			</div>
		{/if}
	</div>

	{#if kind === 'category_distribution'}
		<CategoryReading {categories} {loading} />
	{:else}
		<!-- The detailed view covers the page, so it is given the words this block names itself with. -->
		<DistributionReading {distribution} {loading} {stat} {openOn} {heading} {subheading} />
	{/if}

	<!-- A changed answer must never look like the default one. -->
	{#if customRoster && answered}
		<p><span class="tag micro">Custom roster</span></p>
	{/if}

	<!-- From the number to how it was reached. -->
	<p class="about-link small"><a href={aboutHref}>How this model works</a></p>
</section>

<style>
	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		border-top-color: var(--plane-accent);
	}

	header h2 {
		margin-bottom: var(--space-1);
	}

	/* Full strength beside the muted line above it, so the reader meets it before the figure. */
	.thin {
		margin-top: var(--space-2);
	}

	/* One figure, or two side by side where the answer carries a second reading. They wrap rather
	   than shrink, so neither is ever set smaller than the other. */
	.lead {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3) var(--space-6);
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
</style>
