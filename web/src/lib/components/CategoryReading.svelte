<script lang="ts">
	import Reading from '$lib/components/Reading.svelte';
	import { sentenceCase } from '$lib/models';
	import { CATEGORY_DECIMALS, sharePercentages } from '$lib/odds';

	import type { CategoryAnswer } from '$lib/odds';

	type Props = {
		/** The prediction result, or null while it is loading. */
		categories: CategoryAnswer | null;
		loading: boolean;
		/** Animates the bars when a result arrives on the client. */
		animateBars?: boolean;
	};

	let { categories, loading, animateBars = false }: Props = $props();

	/** Number of placeholder rows. A yes or no result has two. */
	const RESERVED_ROWS = 2;

	const rows = $derived.by(() => {
		if (!categories) return [];

		const shares = sharePercentages(categories.probabilities, CATEGORY_DECIMALS);

		return categories.names.map((name, index) => ({
			name,
			share: shares[index],
			width: `${categories.probabilities[index] * 100}%`
		}));
	});
</script>

<Reading answered={categories !== null && !loading}>
	{#snippet answer()}
		<dl class:drawing={animateBars}>
			{#each rows as row, index (row.name)}
				<div class="row">
					<dt class="small">{sentenceCase(row.name)}</dt>
					<dd class="figure">{row.share}%</dd>
					<div class="track" aria-hidden="true">
						<div
							class="bar"
							style:width={row.width}
							style:animation-delay={`${Math.min(index * 40, 80)}ms`}
						></div>
					</div>
				</div>
			{/each}
		</dl>
	{/snippet}

	{#snippet skeleton()}
		<dl aria-hidden="true">
			{#each Array(RESERVED_ROWS) as _, row (row)}
				<div class="row">
					<div class="reserved name" class:waiting={loading}></div>
					<div class="reserved track" class:waiting={loading}></div>
				</div>
			{/each}
		</dl>
	{/snippet}
</Reading>

<style>
	dl {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: baseline;
		gap: var(--space-1) var(--space-3);
	}

	dd {
		margin: 0;
	}

	.track {
		grid-column: 1 / -1;
		height: var(--space-4);
		background: var(--surface-sunken);
	}

	.bar {
		height: 100%;
		background: var(--chart-neutral);
	}

	.drawing .bar {
		animation-name: run;
		animation-duration: var(--motion);
		animation-timing-function: var(--ease-in);
		animation-fill-mode: backwards;
	}

	@keyframes run {
		from {
			clip-path: inset(0 100% 0 0);
		}

		to {
			clip-path: inset(0);
		}
	}

	.reserved.name {
		grid-column: 1 / -1;
		width: calc(var(--space-8) * 1.5);
		max-width: 60%;
		height: calc(var(--type-small) * 1.5);
	}
</style>
