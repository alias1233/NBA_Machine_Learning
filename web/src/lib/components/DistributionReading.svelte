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
		/** True where the block stands for an answer rather than being one, so it owns no address bar. */
		example?: boolean;
	};

	let { distribution, loading, stat, openOn, heading, subheading, example = false }: Props =
		$props();
</script>

<div class="surface reading" use:flowingHeight>
	<div>
		{#if distribution && !loading}
			<DistributionAnswer {distribution} {stat} {openOn} {heading} {subheading} {example} />
		{:else}
			<!-- Reserved space at the size the answer will take. It pulses only while one is on its
			     way: standing before the first prediction it keeps still, because nothing is coming
			     until the reader asks for it. -->
			<div class="skeleton" aria-hidden="true">
				<!-- The tracks the odds land in, in the row they will be read on. Nothing here is named:
				     the words belong to the answer, and a block standing empty has not been told which
				     model it is waiting for or whether that model reads against a line at all. -->
				<div class="odds">
					{#each [0, 1, 2] as track (track)}
						<div>
							<div class="reserved label" class:waiting={loading}></div>
							<div class="reserved figure" class:waiting={loading}></div>
						</div>
					{/each}
				</div>

				<div class="reserved chart" class:waiting={loading}></div>
				<div class="reserved handle" class:waiting={loading}></div>
				<div class="reserved row" class:waiting={loading}></div>
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

	/* The bars, plus the readout above them and the outcome marks below them, which is the whole of
	   what a drawn chart takes. */
	.reserved.chart {
		height: calc(var(--chart-height) + var(--space-5) * 2);
	}

	.reserved.handle,
	.reserved.row {
		height: var(--tap-target);
	}

	/* The height a micro label takes on its own line, so the row is the size the named odds land in
	   however the reserved space is drawn. */
	.reserved.label {
		width: 3.25rem;
		height: calc(var(--type-micro) * 1.4);
	}

	.reserved.figure {
		height: var(--type-figure);
		margin-top: var(--space-1);
	}
</style>
