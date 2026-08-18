<!--
	An answer that is a chance per named category.

	The categories have no order, so there is no line to read against and nothing to drag. Every
	category is drawn, which makes this the whole answer rather than a view of one, so nothing sits
	behind it either.

	A category's name and its chance share a line above a bar of the full width, so the bars are the
	same size whatever the figures over them are. Bars are neutral, the same as a chart with no line
	set, because nothing here splits them.
-->
<script lang="ts">
	import { sentenceCase } from '$lib/models';
	import { flowingHeight } from '$lib/motion';
	import { CATEGORY_DECIMALS, sharePercentages } from '$lib/odds';

	import type { CategoryAnswer } from '$lib/odds';

	type Props = {
		/** The finished answer, or null while one is being worked out. */
		categories: CategoryAnswer | null;
		loading: boolean;
	};

	let { categories, loading }: Props = $props();

	/** What a yes or no answer takes, which is every model answering this way today. */
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

<div class="surface reading" use:flowingHeight>
	<div>
		{#if categories && !loading}
			<dl>
				{#each rows as row (row.name)}
					<div class="row">
						<dt class="small">{sentenceCase(row.name)}</dt>
						<dd class="figure">{row.share}%</dd>
						<div class="track" aria-hidden="true">
							<div class="bar" style:width={row.width}></div>
						</div>
					</div>
				{/each}
			</dl>
		{:else}
			<dl aria-hidden="true">
				{#each Array(RESERVED_ROWS) as _, row (row)}
					<div class="row">
						<div class="reserved name" class:waiting={loading}></div>
						<div class="reserved track" class:waiting={loading}></div>
					</div>
				{/each}
			</dl>
		{/if}
	</div>
</div>

<style>
	/* It holds the height of whatever is in it, so the skeleton flows into the answer. */
	.reading {
		overflow: clip;
	}

	dl {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	/* The name takes what it needs and the figure sits at the far end of the same line, so the bar
	   under them is the full width in every row however long a figure runs. */
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

	/* No radius. A rounded bar misreports its own length. */
	.bar {
		height: 100%;
		background: var(--chart-neutral);
		transition: width var(--motion-slow) var(--ease-in);
	}

	/* Given its width, because a name it is standing in for has none to take. */
	.reserved.name {
		grid-column: 1 / -1;
		width: calc(var(--space-8) * 1.5);
		max-width: 60%;
		height: var(--type-figure);
	}
</style>
