<script lang="ts">
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';

	import DetailedChart from '$lib/components/DetailedChart.svelte';
	import DistributionChart from '$lib/components/DistributionChart.svelte';
	import LineControl from '$lib/components/LineControl.svelte';
	import OddsReadout from '$lib/components/OddsReadout.svelte';
	import {
		calculateOdds,
		chartRange,
		defaultLine,
		expectedValue,
		figureText,
		mostLikelyOutcomes,
		oddsPercentages,
		outcomes
	} from '$lib/odds';

	import type { Distribution } from '$lib/odds';

	type Props = {
		distribution: Distribution;
		/** Name of the predicted stat, in lowercase. */
		stat: string;
		/** Line from the URL, if there is one. */
		openOn: number | null;
		/** Title of the result. */
		heading: string;
		subheading: string;
		/** True when the block is a static example and not a real prediction. */
		example?: boolean;
		/** Animates the bars when a result arrives on the client. */
		animateBars?: boolean;
	};

	let {
		distribution,
		stat,
		openOn,
		heading,
		subheading,
		example = false,
		animateBars = false
	}: Props = $props();

	const URL_SYNC_DELAY = 300;

	const expected = $derived(expectedValue(distribution));
	const range = $derived(chartRange(distribution));
	const rangeOutcomes = $derived(outcomes(distribution).slice(range.first, range.last + 1));
	const limits = $derived({
		lowest: rangeOutcomes[0].lowest,
		highest: rangeOutcomes.at(-1)!.highest
	});

	// svelte-ignore state_referenced_locally
	let line = $state(
		Math.min(
			Math.max(openOn ?? defaultLine(expected), limits.lowest),
			limits.highest
		)
	);

	const odds = $derived(calculateOdds(distribution, line));
	const spoken = $derived(oddsPercentages(odds));

	/** True when the chart is open in full screen. */
	let detailed = $state(false);

	const likeliest = $derived(mostLikelyOutcomes(distribution, 1)[0]);

	const summary = $derived(
		[
			`Expected ${figureText(distribution, expected)} ${stat}.`,
			`Most likely ${likeliest.label} ${stat}.`,
			`Under ${line}, ${spoken.under} percent.`,
			`Push ${line}, ${spoken.push} percent.`,
			`Over ${line}, ${spoken.over} percent.`
		].join(' ')
	);

	let opened = false;

	$effect(() => {
		const chosen = line;

		if (example) return;

		if (!opened) {
			opened = true;
			return;
		}

		const timer = setTimeout(() => {
			// Uses location.href because replaceState does not update page.url.
			const url = new URL(location.href);
			url.searchParams.set('line', String(chosen));

			replaceState(url, page.state);
		}, URL_SYNC_DELAY);

		return () => clearTimeout(timer);
	});
</script>

<div class="held">
	<OddsReadout {odds} />

	<div class="plot">
		<DistributionChart {distribution} {stat} {line} {range} {summary} animate={animateBars} />
	</div>
</div>

<LineControl id="line" bind:line {distribution} {range}>
	<button
		type="button"
		class="button button--quiet"
		aria-haspopup="dialog"
		onclick={() => (detailed = true)}
	>
		See the full chart
	</button>
</LineControl>

{#if detailed}
	<DetailedChart
		{distribution}
		{stat}
		{heading}
		{subheading}
		bind:line
		onclose={() => (detailed = false)}
	/>
{/if}

<style>
	.held {
		display: grid;
		gap: var(--space-4);
	}

	.plot {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-width: 0;
	}
</style>
