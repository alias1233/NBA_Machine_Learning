<!--
	The whole prediction, one bar per whole number outcome.

	Bars are discrete because the outcomes are. A smooth curve would claim the model answers in
	fractions of a point. The line splits the chart and the two masses either side of it are the odds,
	so the split the readout reports is always the split the chart shows.

	It draws on the surface its caller owns, because the chart, the line and the odds are one object.
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import { MOTION_SLOW } from '$lib/motion';
	import { outcomes } from '$lib/odds';

	type Props = {
		probabilities: number[];
		minimumValue: number;
		/** What the model predicts, lowercase, for the line a bar reads out as. */
		stat: string;
		line: number;
		/** The outcomes to draw. Its caller owns it, because the handle travels across the same run. */
		range: { first: number; last: number };
		/** Stands in for the drawing when it cannot be seen. */
		summary: string;
	};

	let { probabilities, minimumValue, stat, line, range, summary }: Props = $props();

	// A one pixel gap needs a bar this wide to still read as a bar. Below it the bars run together
	// into one silhouette, which is better than a comb of slivers.
	const GAP_ABOVE_WIDTH = 6;

	const bars = $derived(
		outcomes(probabilities, minimumValue).filter(
			({ value }) => value >= range.first && value <= range.last
		)
	);

	const tallest = $derived(Math.max(...bars.map(({ probability }) => probability)));

	// Unmeasured on the server, and a gap is the usual answer, so it holds one until it knows better.
	let width = $state(0);
	const gap = $derived(
		width === 0 || (width - bars.length + 1) / bars.length >= GAP_ABOVE_WIDTH ? 1 : 0
	);

	// Every fifth outcome, plus the two ends where they would not crowd one.
	const marks = $derived.by(() => {
		const fives: number[] = [];
		for (let value = Math.ceil(range.first / 5) * 5; value <= range.last; value += 5) fives.push(value);

		const first = fives[0] === undefined || fives[0] - range.first >= 3 ? [range.first] : [];
		const last = fives.at(-1) === undefined || range.last - fives.at(-1)! >= 3 ? [range.last] : [];

		return [...new Set([...first, ...fives, ...last])];
	});

	let reading = $state<number | null>(null);
	let drawn = $state(false);

	const read = $derived(bars.find(({ value }) => value === reading) ?? null);

	const percent = (probability: number) => `${(probability * 100).toFixed(1)}%`;
	const positionOf = (value: number) => ((value - range.first + 0.5) / bars.length) * 100;

	function readAt(event: PointerEvent) {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
		const index = Math.floor(((event.clientX - box.left) / box.width) * bars.length);

		reading = bars[Math.min(Math.max(index, 0), bars.length - 1)]?.value ?? null;
	}

	function readByKey(event: KeyboardEvent) {
		const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
		if (step === 0) return;

		event.preventDefault();
		reading = Math.min(Math.max((reading ?? Math.round(line)) + step, range.first), range.last);
	}

	// Once the draw is over the class comes off, so a bar the line brings into range later arrives
	// without replaying it.
	onMount(() => {
		const timer = setTimeout(() => (drawn = true), MOTION_SLOW);

		return () => clearTimeout(timer);
	});
</script>

<figure style="--columns: {bars.length}; --gap: {gap}px">
	<p class="readout small muted numeric" aria-hidden="true">
		{read ? `${read.value} ${stat}, ${percent(read.probability)}` : ''}
	</p>

	<!-- One focusable element, not sixty. What it says is in the label and in the table below. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
	<div
		class="bars"
		class:drawing={!drawn}
		role="img"
		aria-label={summary}
		tabindex="0"
		bind:clientWidth={width}
		onpointermove={readAt}
		onpointerleave={() => (reading = null)}
		onkeydown={readByKey}
		onblur={() => (reading = null)}
	>
		{#each bars as bar (bar.value)}
			<div
				class="bar"
				class:over={bar.value > line}
				class:under={bar.value < line}
				class:push={bar.value === line}
				class:reading={bar.value === reading}
				style="height: {(bar.probability / tallest) * 100}%"
			></div>
		{/each}
	</div>

	<figcaption class="marks" aria-hidden="true">
		{#each marks as value (value)}
			<span class="small muted numeric" style="left: {positionOf(value)}%">{value}</span>
		{/each}
	</figcaption>
</figure>

<style>
	figure {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	/* Reserved whether or not a bar is being read, so the chart never moves under the pointer. */
	.readout {
		min-height: var(--space-5);
		max-width: none;
		text-align: right;
	}

	.bars {
		display: grid;
		grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
		column-gap: var(--gap);
		align-items: end;
		height: calc(var(--space-8) * 2);
		touch-action: pan-y;
	}

	/* No radius. A rounded bar misreports its own height. */
	.bar {
		background: var(--chart-neutral);
		transform-origin: bottom;
	}

	.bar.over {
		background: var(--over);
	}

	.bar.under {
		background: var(--under);
	}

	/* The outcome the line lands on. A colour of its own, because a push is a result rather than the
	   absence of one. */
	.bar.push {
		background: var(--push);
	}

	.bar.reading {
		outline: var(--rule-accent);
	}

	/* Once, on first render. Recolouring as the line moves is instant and never runs this. */
	.drawing .bar {
		animation: draw var(--motion-slow) var(--ease-in) backwards;
	}

	@keyframes draw {
		from {
			transform: scaleY(0);
		}
	}

	/* The marks are placed by value, so they line up inside the same box the bars are drawn in and
	   the strip has to be told how tall to be. */
	.marks {
		position: relative;
		height: var(--space-5);
	}

	.marks span {
		position: absolute;
		transform: translateX(-50%);
		white-space: nowrap;
	}

	@media (min-width: 64rem) {
		.bars {
			height: calc(var(--space-8) * 3);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.drawing .bar {
			animation: none;
		}
	}
</style>
