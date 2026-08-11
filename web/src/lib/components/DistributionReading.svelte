<!--
	The reading for an answer that is a chance per whole number outcome, or per short run of them.

	The chart, the line and the odds are one object on one surface, which is what puts data on neutral
	ground inside an inverted container. The surface holds the height of whatever is in it, so the
	skeleton flows into the answer and nothing inside it carries a motion of its own.

	Everything an answer is read with is drawn only while there is an answer. Until then this is
	reserved space at the size that answer will take, carrying no figure, no line and no way into the
	detailed view, whether it stands before the first answer or between two.
-->
<script lang="ts">
	import DistributionAnswer from '$lib/components/DistributionAnswer.svelte';
	import { flowingHeight } from '$lib/motion';

	import type { Distribution } from '$lib/odds';

	type Props = {
		/** The finished answer, or null while one is being worked out. */
		distribution: Distribution | null;
		loading: boolean;
		/** What the model predicts, lowercase. */
		stat: string;
		/** The line the address bar already names, if it names one. */
		openOn: number | null;
		/** What the answer names itself, which the detailed view carries because it covers the page. */
		heading: string;
		subheading: string;
	};

	let { distribution, loading, stat, openOn, heading, subheading }: Props = $props();
</script>

<div class="surface reading" use:flowingHeight>
	<div>
		{#if distribution && !loading}
			<DistributionAnswer {distribution} {stat} {openOn} {heading} {subheading} />
		{:else}
			<div class="skeleton" aria-hidden="true">
				<!-- The three the odds land in, named but unanswered, in the row they will be read on. -->
				<div class="odds">
					{#each ['Over', 'Under', 'Push'] as label (label)}
						<div>
							<p class="micro muted">{label}</p>
							<div class="waiting figure"></div>
						</div>
					{/each}
				</div>

				<div class="waiting chart"></div>
				<div class="waiting handle"></div>
				<div class="waiting row"></div>
			</div>
		{/if}
	</div>
</div>

<style>
	/* The surface holds the height, so what it holds is laid out one level in. */
	.reading {
		overflow: clip;
	}

	.skeleton {
		display: grid;
		gap: var(--space-2);
	}

	/* The same tracks the finished odds take, so the reserved space is the space they land in, and the
	   same distance above the chart. */
	.odds {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, var(--figure-column)));
		gap: var(--space-3);
		margin-bottom: var(--space-2);
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

	/* The bars, plus the readout above them and the outcome marks below them, which is the whole of
	   what a drawn chart takes. */
	.waiting.chart {
		height: calc(var(--chart-height) + var(--space-5) * 2);
	}

	.waiting.handle,
	.waiting.row {
		height: var(--tap-target);
	}

	.waiting.figure {
		height: var(--type-figure);
		margin-top: var(--space-1);
	}
</style>
