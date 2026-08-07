<!--
	The answer the page exists to produce. See section 10.8.

	One box, three states. Empty, loading and answered all render the same scaffold at the same size,
	so the page never jumps when a prediction lands. R10.30 and R10.31.

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
	import {
		calculateOdds,
		chartRange,
		defaultLine,
		mostLikelyOutcomes,
		oddsPercentages,
		outcomes
	} from '$lib/odds';

	import type { Prediction } from '$lib/types';

	type Props = {
		/** The finished answer, or null when nothing has been asked yet. */
		prediction: Prediction | null;
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
		/** The family's own page, so a reader can get from the number to how it was reached. R11.11. */
		aboutHref: string;
		/** Whether this answer was asked for with a changed roster. R10.30. */
		customRoster: boolean;
	};

	let { prediction, loading, stat, heading, subheading, openOn, aboutHref, customRoster }: Props =
		$props();

	const URL_SYNC_DELAY = 300;
	const MOST_LIKELY = 5;

	const lowest = $derived(prediction?.minimum_value ?? 0);
	const highest = $derived(
		prediction ? prediction.minimum_value + prediction.probabilities.length - 1 : 0
	);

	// Deliberately the opening value only. After that the reader owns it, and a new prediction
	// remounts this component with its own.
	// svelte-ignore state_referenced_locally
	let line = $state(
		prediction
			? Math.min(Math.max(openOn ?? defaultLine(prediction.expected_value), lowest), highest)
			: 0
	);

	const odds = $derived(
		prediction
			? calculateOdds(prediction.probabilities, line, prediction.minimum_value)
			: { over: 0, under: 0, push: 0 }
	);
	const spoken = $derived(oddsPercentages(odds, line));

	const likeliest = $derived(
		prediction
			? mostLikelyOutcomes(prediction.probabilities, MOST_LIKELY, prediction.minimum_value)
			: []
	);

	// One range, read by the chart it draws and by the handle that travels across it.
	const range = $derived(
		prediction ? chartRange(prediction.probabilities, prediction.minimum_value, line) : null
	);

	// The push sentence is always present, the same rule the readout follows. On a half number it
	// reads 0.0 percent, because a half number cannot be landed on. R10.23.
	const summary = $derived(
		prediction
			? [
					`Expected ${prediction.expected_value.toFixed(1)} ${stat}.`,
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
		if (!prediction || !opened) {
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

<!-- The one container carrying the accent top edge unhovered, because it is the answer. R10.9. -->
<section class="block answer">
	<header>
		<h2>{heading}</h2>
		{#if subheading}
			<p class="muted small">{subheading}</p>
		{/if}
	</header>

	<div class="expected">
		<p class="micro muted">Expected</p>
		{#if prediction && !loading}
			<p class="figure-lead">{prediction.expected_value.toFixed(1)}</p>
		{:else}
			<div class="waiting lead"></div>
		{/if}
	</div>

	<!-- The chart, the line and the odds are one object on one surface, which is what puts data on
	     neutral ground inside an inverted container. R3.4 and section 10.7. -->
	<div class="surface reading">
		{#if prediction && range && !loading}
			<div class="plot">
				<DistributionChart
					probabilities={prediction.probabilities}
					minimumValue={prediction.minimum_value}
					{stat}
					{line}
					{range}
					{summary}
				/>
				<LineControl bind:line {lowest} {highest} {range} />

				<!-- Behind the drawing, available to anyone. R10.26. -->
				<details>
					<summary class="small link">All outcomes</summary>

					<div class="scroll">
						<table class="small numeric">
							<thead>
								<tr>
									<th scope="col">{sentenceCase(stat)}</th>
									<th scope="col">Chance</th>
								</tr>
							</thead>
							<tbody>
								{#each outcomes(prediction.probabilities, prediction.minimum_value) as outcome (outcome.value)}
									<tr>
										<td>{outcome.value}</td>
										<td>{(outcome.probability * 100).toFixed(1)}%</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</details>
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

	<div class="likely">
		<h3>Most likely</h3>

		{#if prediction && !loading}
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

	<!-- A changed answer must never look like the default one. R10.30. -->
	{#if customRoster && prediction && !loading}
		<p><span class="tag micro">Custom roster</span></p>
	{/if}

	<!-- From the number to how it was reached, which is the second of the two links in R11.11. -->
	<p class="small"><a href={aboutHref}>How this model works</a></p>
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

	.expected p:first-child {
		margin-bottom: var(--space-2);
	}

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

	/* Section 14 calls this a link, so it takes the link role from app.css. */
	summary {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
		cursor: pointer;
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
	   skeleton on a block is drawn in the block's own hairline. */
	.waiting {
		background: var(--hairline-block);
		border-radius: var(--radius);
	}

	.waiting.lead {
		height: var(--type-figure-lead);
		max-width: calc(var(--space-8) * 2);
	}

	.waiting.row {
		width: 100%;
		max-width: calc(var(--space-8) * 3);
		height: var(--type-body);
		align-self: center;
	}

	/* Inside the surface the page-side tokens apply again, so the skeleton is the sunken plane. */
	.waiting.chart,
	.waiting.handle,
	.waiting.figure {
		background: var(--surface-sunken);
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

	/* The odds sit beside the chart once there is room for both, on the same surface. Section 10.7. */
	@media (min-width: 64rem) {
		.reading {
			grid-template-columns: minmax(0, 1fr) auto;
		}

		.waiting.chart {
			height: calc(var(--space-8) * 3);
		}

		.waiting-odds {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
