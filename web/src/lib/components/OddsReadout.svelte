<script lang="ts">
	import { rolling } from '$lib/motion';
	import { oddsPercentages } from '$lib/odds';

	import type { LineOdds } from '$lib/odds';

	type Props = {
		odds: LineOdds;
		large?: boolean;
	};

	let { odds, large = false }: Props = $props();

	const over = rolling(() => odds.over);
	const under = rolling(() => odds.under);
	const push = rolling(() => odds.push);

	const shown = $derived(
		oddsPercentages({ over: over.current, under: under.current, push: push.current })
	);
</script>

<dl class:large>
	<div class="under" data-explain="under">
		<dt class="micro">Under</dt>
		<dd class="figure">{shown.under}%</dd>
	</div>

	<div class="push" data-explain="push">
		<dt class="micro">Push</dt>
		<dd class="figure">{shown.push}%</dd>
	</div>

	<div class="over" data-explain="over">
		<dt class="micro">Over</dt>
		<dd class="figure">{shown.over}%</dd>
	</div>
</dl>

<style>
	dl {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, var(--figure-column)));
	}

	dl > div {
		width: max-content;
		max-width: 100%;
	}

	dt {
		color: var(--ink-muted);
	}

	dd {
		margin: var(--space-1) 0 0;
		white-space: nowrap;
	}

	.over dd {
		color: var(--over);
	}

	.under dd {
		color: var(--under);
	}

	.push dd {
		color: var(--push);
	}

	dl.large {
		container-type: inline-size;
		grid-template-columns: repeat(3, minmax(0, var(--figure-column-large)));
		gap: var(--space-4);
	}

	dl.large dd {
		font-size: clamp(var(--type-figure), 8cqi, var(--type-figure-large));
	}
</style>
