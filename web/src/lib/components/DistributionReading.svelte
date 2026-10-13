<script lang="ts">
	import DistributionAnswer from '$lib/components/DistributionAnswer.svelte';
	import Reading from '$lib/components/Reading.svelte';

	import type { Distribution } from '$lib/odds';

	type Props = {
		/** The prediction result, or null while it is loading. */
		distribution: Distribution | null;
		loading: boolean;
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
		loading,
		stat,
		openOn,
		heading,
		subheading,
		example = false,
		animateBars = false
	}: Props = $props();
</script>

<Reading answered={distribution !== null && !loading}>
	{#snippet answer()}
		<DistributionAnswer
			distribution={distribution!}
			{stat}
			{openOn}
			{heading}
			{subheading}
			{example}
			{animateBars}
		/>
	{/snippet}

	{#snippet skeleton()}
		<div class="skeleton" aria-hidden="true">
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
	{/snippet}
</Reading>

<style>
	.skeleton {
		display: grid;
		gap: var(--space-2);
	}

	.odds {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, var(--figure-column)));
		gap: var(--space-3);
		margin-bottom: var(--space-2);
	}

	.reserved.chart {
		height: calc(var(--chart-height) + var(--space-5) * 2);
	}

	.reserved.handle,
	.reserved.row {
		height: var(--tap-target);
	}

	.reserved.label {
		width: 3.25rem;
		height: calc(var(--type-micro) * 1.4);
	}

	.reserved.figure {
		height: calc(var(--type-figure) * 1.2);
		margin-top: var(--space-1);
	}
</style>
