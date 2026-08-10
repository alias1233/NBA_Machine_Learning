<!--
	An answer that is a chance per named category.

	The categories have no order, so there is no line to read against and nothing to drag. Every
	category is drawn, which makes this the whole answer rather than a view of one, so nothing sits
	behind it either.

	Bars are neutral, the same as a chart with no line set, because nothing here splits them.
-->
<script lang="ts">
	import { sentenceCase } from '$lib/models';
	import { sharePercentages } from '$lib/odds';

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

		const shares = sharePercentages(categories.probabilities);

		return categories.names.map((name, index) => ({
			name,
			share: shares[index],
			width: `${categories.probabilities[index] * 100}%`
		}));
	});
</script>

<div class="surface reading">
	{#if categories && !loading}
		<dl>
			{#each rows as row (row.name)}
				<div class="row">
					<dt class="small">{sentenceCase(row.name)}</dt>
					<div class="track" aria-hidden="true"><div class="bar" style:width={row.width}></div></div>
					<dd class="figure">{row.share}%</dd>
				</div>
			{/each}
		</dl>
	{:else}
		<dl aria-hidden="true">
			{#each Array(RESERVED_ROWS) as _, row (row)}
				<div class="row"><div class="waiting"></div></div>
			{/each}
		</dl>
	{/if}
</div>

<style>
	dl {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	/* The name and the figure take what they need and the bar takes the rest, so two rows line up
	   however long a category is named. */
	.row {
		display: grid;
		grid-template-columns: minmax(0, auto) minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--space-3);
		min-height: var(--tap-target);
	}

	dd {
		margin: 0;
		text-align: right;
	}

	.track {
		height: var(--space-4);
		background: var(--surface-sunken);
	}

	/* No radius. A rounded bar misreports its own length. */
	.bar {
		height: 100%;
		background: var(--chart-neutral);
		transition: width var(--motion-slow) var(--ease-in);
	}

	/* Reserved space, drawn as the sunken plane and pulsing so the box reads as loading. */
	.waiting {
		grid-column: 1 / -1;
		height: var(--space-4);
		background: var(--surface-sunken);
		border-radius: var(--radius);
		animation: pulse var(--loading-pulse) var(--ease-in-out) infinite alternate;
	}

	@keyframes pulse {
		to {
			opacity: 0.4;
		}
	}
</style>
