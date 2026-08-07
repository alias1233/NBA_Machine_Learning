<!--
	What the line settles at. Over first, then under, then push. See section 10.7.

	Every answer is a sum over probabilities the page already holds, so moving the line asks the
	server for nothing. The words are always present and always in this order, because around one man
	in twelve cannot separate the two hues. R3.8.

	Push can only be landed on by a whole number line, so on a half number the box stays and its
	contents go. A readout that resizes as the slider passes a whole number is the bug this prevents.
	R10.18.
-->
<script lang="ts">
	import { rolling } from '$lib/motion';
	import { hasPush, oddsPercentages } from '$lib/odds';

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

	<div class="push" class:landable={hasPush(line)}>
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

	/* The box is held at every line. Only what is in it comes and goes. */
	.push:not(.landable) {
		visibility: hidden;
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
