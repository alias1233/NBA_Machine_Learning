<!--
	What the line settles at. Over first, then under, then push.

	Every answer is a sum over probabilities the page already holds, so moving the line asks the
	server for nothing. 

	All three figures are shown at every line. Push reads 0.0 percent on a half number, because a
	half number cannot be landed on. Dropping it instead would blink a figure in and out as the
	slider passed each whole number. Where an outcome covers a run of whole numbers, a push is that
	outcome's even share of the one number the line sits on.

	All three roll towards whatever the new line settles at, including a roll down to nothing, so the
	three always read as one movement.

	Each figure sits in a box of its own, as wide as the widest one it can reach, so a figure growing
	a digit as the line is dragged moves nothing beside it.
-->
<script lang="ts">
	import { rolling } from '$lib/motion';
	import { oddsPercentages } from '$lib/odds';

	import type { LineOdds } from '$lib/odds';

	type Props = {
		odds: LineOdds;
		/** True where the three are the readout of a whole screen rather than a corner of a block. */
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
	/* Tracks sized by the widest figure they can reach rather than by the figure in them, so nothing
	   laid out beside them is resized as the line is dragged. The cap is a ceiling, so on a narrow
	   screen the three share what there is instead of running past the edge. */
	dl {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, var(--figure-column)));
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

	/* Read from across a screen rather than from a column, so the figures are set larger and each
	   takes the box that size of figure needs. */
	dl.large {
		grid-template-columns: repeat(3, minmax(0, var(--figure-column-large)));
		gap: var(--space-4);
	}

	dl.large dd {
		font-size: var(--type-figure-large);
	}
</style>
