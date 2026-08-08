<!--
	What the line settles at. Over first, then under, then push.

	Every answer is a sum over probabilities the page already holds, so moving the line asks the
	server for nothing. The words are always present and always in this order, because around one man
	in twelve cannot separate the two hues.

	All three figures are shown at every line. Push reads 0.0 percent on a half number, because a
	half number cannot be landed on. Dropping it instead would blink a figure in and out as the
	slider passed each whole number.
-->
<script lang="ts">
	import { rolling } from '$lib/motion';
	import { oddsPercentages } from '$lib/odds';

	import type { LineOdds } from '$lib/odds';

	type Props = {
		odds: LineOdds;
		line: number;
	};

	let { odds, line }: Props = $props();

	const over = rolling(() => odds.over);
	const under = rolling(() => odds.under);
	const push = rolling(() => odds.push);

	const shown = $derived(
		oddsPercentages({ over: over.current, under: under.current, push: push.current }, line)
	);
</script>

<dl>
	<div class="over">
		<dt class="micro">Over</dt>
		<dd class="figure">{shown.over}%</dd>
	</div>

	<div class="under">
		<dt class="micro">Under</dt>
		<dd class="figure">{shown.under}%</dd>
	</div>

	<div class="push">
		<dt class="micro">Push</dt>
		<dd class="figure">{shown.push}%</dd>
	</div>
</dl>

<style>
	dl {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-3);
	}

	dt {
		color: var(--ink-muted);
	}

	dd {
		margin: var(--space-1) 0 0;
	}

	.over dd {
		color: var(--over);
	}

	.under dd {
		color: var(--under);
	}

	.push dd {
		color: var(--chart-neutral);
	}

	/* Beside the chart from here, so the three stack at the top of the column instead of sitting
	   across it. */
	@media (min-width: 64rem) {
		dl {
			grid-template-columns: minmax(0, 1fr);
			align-content: start;
			gap: var(--space-4);
		}
	}
</style>
