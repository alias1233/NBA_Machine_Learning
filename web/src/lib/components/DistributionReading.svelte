<!--
	An answer that is a chance for every whole number outcome.

	The chart, the line and the odds are one object on one surface, which is what puts data on neutral
	ground inside an inverted container.

	It owns the chosen line, because the chart and the odds have to agree on it, and it writes that
	line back into the address bar so a prediction is shareable at the line it is read on. The write
	replaces rather than pushes, so dragging the handle does not fill the back button.
-->
<script lang="ts">
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';

	import DistributionChart from '$lib/components/DistributionChart.svelte';
	import LineControl from '$lib/components/LineControl.svelte';
	import OddsReadout from '$lib/components/OddsReadout.svelte';
	import { sentenceCase } from '$lib/models';
	import { flow } from '$lib/motion';
	import {
		calculateOdds,
		chartRange,
		defaultLine,
		expectedValue,
		mostLikelyOutcomes,
		oddsPercentages,
		outcomes
	} from '$lib/odds';

	import type { Distribution } from '$lib/odds';

	type Props = {
		/** The finished answer, or null while one is being worked out. */
		distribution: Distribution | null;
		loading: boolean;
		/** What the model predicts, lowercase. */
		stat: string;
		/** The line the address bar already names, if it names one. */
		openOn: number | null;
	};

	let { distribution, loading, stat, openOn }: Props = $props();

	const URL_SYNC_DELAY = 300;
	const MOST_LIKELY = 5;

	const lowest = $derived(distribution?.minimumValue ?? 0);
	const highest = $derived(
		distribution ? distribution.minimumValue + distribution.probabilities.length - 1 : 0
	);

	const expected = $derived(
		distribution ? expectedValue(distribution.probabilities, distribution.minimumValue) : 0
	);

	// Deliberately the opening value only. After that the reader owns it, and a new prediction
	// remounts this component with its own.
	// svelte-ignore state_referenced_locally
	let line = $state(
		distribution ? Math.min(Math.max(openOn ?? defaultLine(expected), lowest), highest) : 0
	);

	const odds = $derived(
		distribution
			? calculateOdds(distribution.probabilities, line, distribution.minimumValue)
			: { over: 0, under: 0, push: 0 }
	);
	const spoken = $derived(oddsPercentages(odds, line));

	/** Whether the full table behind the drawing is open. */
	let listing = $state(false);

	const likeliest = $derived(
		distribution
			? mostLikelyOutcomes(distribution.probabilities, MOST_LIKELY, distribution.minimumValue)
			: []
	);

	// One range, read by the chart it draws and by the handle that travels across it.
	const range = $derived(
		distribution ? chartRange(distribution.probabilities, distribution.minimumValue, line) : null
	);

	// The push sentence is always present, the same rule the readout follows. On a half number it
	// reads 0.0 percent, because a half number cannot be landed on.
	const summary = $derived(
		distribution
			? [
					`Expected ${expected.toFixed(1)} ${stat}.`,
					`Most likely ${likeliest[0].value} ${stat}.`,
					`Over ${line}, ${spoken.over} percent.`,
					`Under ${line}, ${spoken.under} percent.`,
					`Push ${line}, ${spoken.push} percent.`
				].join(' ')
			: ''
	);

	let opened = false;

	$effect(() => {
		const chosen = line;

		// The first run is the value the page opened on, which the address bar already agrees with.
		if (!distribution || !opened) {
			opened = true;
			return;
		}

		const timer = setTimeout(() => {
			// The live URL, not page.url, because a shallow write does not refresh page.url and this
			// would put back whatever the last one replaced.
			const url = new URL(location.href);
			url.searchParams.set('line', String(chosen));

			replaceState(url, page.state);
		}, URL_SYNC_DELAY);

		return () => clearTimeout(timer);
	});
</script>

<div class="surface reading">
	{#if distribution && range && !loading}
		<div class="plot">
			<DistributionChart
				probabilities={distribution.probabilities}
				minimumValue={distribution.minimumValue}
				{stat}
				{line}
				{range}
				{summary}
			/>
			<LineControl bind:line {lowest} {highest} {range} />

			<!-- Behind the drawing, available to anyone. -->
			<button
				type="button"
				class="outcomes small link"
				aria-expanded={listing}
				onclick={() => (listing = !listing)}
			>
				All outcomes
			</button>

			{#if listing}
				<div class="scroll" transition:flow>
					<table class="small numeric">
						<thead>
							<tr>
								<th scope="col">{sentenceCase(stat)}</th>
								<th scope="col">Chance</th>
							</tr>
						</thead>
						<tbody>
							{#each outcomes(distribution.probabilities, distribution.minimumValue) as outcome (outcome.value)}
								<tr>
									<td>{outcome.value}</td>
									<td>{(outcome.probability * 100).toFixed(1)}%</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>

		<OddsReadout {odds} {line} />
	{:else}
		<div class="plot" aria-hidden="true">
			<div class="waiting chart"></div>
			<div class="waiting handle"></div>
		</div>

		<div class="waiting-odds" aria-hidden="true">
			{#each ['Over', 'Under', 'Push'] as label (label)}
				<div>
					<p class="micro muted">{label}</p>
					<div class="waiting figure"></div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.reading {
		display: grid;
		gap: var(--space-4);
	}

	.plot {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-width: 0;
	}

	/* The copy calls this a link, so it takes the link role from app.css. */
	.outcomes {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* Sixty rows would push everything under them off the screen, so the table scrolls in its own
	   box rather than growing the answer. */
	.scroll {
		max-height: calc(var(--space-8) * 3);
		overflow-y: auto;
	}

	table {
		border-collapse: collapse;
		text-align: left;
	}

	th,
	td {
		padding: var(--space-1) var(--space-4) var(--space-1) 0;
		border-bottom: var(--rule);
	}

	th {
		color: var(--ink-muted);
		font-weight: 600;
	}

	/* Reserved space, drawn as the sunken plane because the surface hands the page-side tokens back.
	   It pulses, so the box reads as loading rather than as a finished empty one. */
	.waiting {
		background: var(--surface-sunken);
		border-radius: var(--radius);
		animation: pulse var(--loading-pulse) var(--ease-in-out) infinite alternate;
	}

	@keyframes pulse {
		to {
			opacity: 0.4;
		}
	}

	.waiting.chart {
		height: calc(var(--space-8) * 2);
	}

	.waiting.handle {
		height: var(--tap-target);
	}

	.waiting.figure {
		height: var(--type-figure);
		margin-top: var(--space-1);
	}

	.waiting-odds {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-3);
	}

	/* The odds sit beside the chart once there is room for both, on the same surface. Their column
	   is the width of the widest figure they can reach, so the chart neither moves when a figure
	   reaches a hundred percent nor leaves a number short of room. */
	@media (min-width: 64rem) {
		.reading {
			grid-template-columns: minmax(0, 1fr) var(--odds-column);
		}

		.waiting.chart {
			height: calc(var(--space-8) * 3);
		}

		.waiting-odds {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
