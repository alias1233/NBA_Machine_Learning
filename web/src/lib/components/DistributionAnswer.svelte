<!--
	A finished answer that is a chance per whole number outcome, or per short run of them, drawn.

	The three odds sit in one row above the chart, so the drawing keeps the full width of the surface
	under them, and the way into the detailed view sits at the end of the line's own row below it.

	It is in the page only while there is an answer to draw, so a new prediction arrives as a new one
	of these and opens on its own line rather than carrying the last one's.

	It owns the chosen line, because the chart, the odds and the detailed view have to agree on it, and
	it writes that line back into the address bar so a prediction is shareable at the line it is read
	on. The write replaces rather than pushes, so dragging the handle does not fill the back button.

	It holds the chart, the line and the odds and nothing else. The ranked outcomes and the full table
	sit one press away, in the detailed view.
-->
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
		highestValue,
		lowestValue,
		mostLikelyOutcomes,
		oddsPercentages
	} from '$lib/odds';

	import type { Distribution } from '$lib/odds';

	type Props = {
		distribution: Distribution;
		/** What the model predicts, lowercase. */
		stat: string;
		/** The line the address bar already names, if it names one. */
		openOn: number | null;
		/** What the answer names itself, which the detailed view carries because it covers the page. */
		heading: string;
		subheading: string;
		/** True where the block stands for an answer rather than being one, so it owns no address bar. */
		example?: boolean;
	};

	let { distribution, stat, openOn, heading, subheading, example = false }: Props = $props();

	const URL_SYNC_DELAY = 300;

	const expected = $derived(expectedValue(distribution));

	// Deliberately the opening value only. After that the reader owns it, and a new answer arrives as
	// a new one of these carrying its own.
	// svelte-ignore state_referenced_locally
	let line = $state(
		Math.min(
			Math.max(openOn ?? defaultLine(expected), lowestValue(distribution)),
			highestValue(distribution)
		)
	);

	const odds = $derived(calculateOdds(distribution, line));
	const spoken = $derived(oddsPercentages(odds));

	/** Whether the chart is being read over the whole screen. */
	let detailed = $state(false);

	const likeliest = $derived(mostLikelyOutcomes(distribution, 1)[0]);

	// One range, read by the chart it draws and by the handle that travels across it.
	const range = $derived(chartRange(distribution, line));

	// The push sentence is always present, the same rule the readout follows. On a half number it
	// reads 0.0 percent, because a half number cannot be landed on.
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

		// A block standing for an answer rather than being one was never asked for, so there is
		// nothing in the address bar for its line to keep in step with.
		if (example) return;

		// The first run is the value the answer opened on, which the address bar already agrees with.
		if (!opened) {
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

<div class="held">
	<OddsReadout {odds} />

	<div class="plot">
		<DistributionChart {distribution} {stat} {line} {range} {summary} />
	</div>
</div>

<!-- The one way out sits at the end of the line's own row. Every outcome, the ranked ones and the
     full table are all through here, so the answer itself stays the chart, the line and the odds. -->
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

<!-- The same surface at the size of the screen, so it sits on this one and takes its colours. It
     floats above the page rather than in it, so it adds nothing to the height held around it. -->
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
