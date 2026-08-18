<!--
	The whole prediction, one bar per outcome the model can answer with.

	Bars are discrete because the outcomes are. A smooth curve would claim the model answers in
	fractions of a point. Where a model answers in buckets, one bar covers that run of whole numbers
	and is that many times wider on the number line, so a line drawn at any value still lands in the
	right place. The line splits the chart and the two masses either side of it are the odds, so the
	split the readout reports is always the split the chart shows.

	It draws on the surface its caller owns, because the chart, the line and the odds are one object.

	Two densities, one drawing, and neither ever travels sideways. In an answer it fills its box. In
	the detailed view it is given a probability axis, a mark for what the model expects, and a figure
	over every bar wide enough to hold one. Everything that cannot fit thins out rather than shrinking
	below legible, because the exact figures are one press away.
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import { MOTION_SLOW } from '$lib/motion';
	import { axisAt, axisSpan, axisTicks, expectedValue, outcomeOf, outcomes } from '$lib/odds';

	import type { ChartRange, Distribution } from '$lib/odds';

	type Props = {
		distribution: Distribution;
		/** What the model predicts, lowercase, for the line a bar reads out as. */
		stat: string;
		line: number;
		/** The outcomes to draw. Its caller owns it, because the handle travels across the same run. */
		range: ChartRange;
		/** Stands in for the drawing when it cannot be seen. */
		summary: string;
		/** The detailed view: a probability axis, what the model expects, and a figure over each bar. */
		detailed?: boolean;
	};

	let { distribution, stat, line, range, summary, detailed = false }: Props = $props();

	// Measured against one column of the drawing, in pixels, because what fits is a question about
	// the bars rather than about the screen.

	/** Below this a gap eats the bar, so the run is drawn as one silhouette rather than as slivers. */
	const GAP_FLOOR = 6;
	/** A gap of this share of the column, so the drawing reads the same at every density. */
	const GAP_SHARE = 12;
	/** Past which a wider bar gains nothing from a wider gap. */
	const GAP_CEILING = 6;
	/** What a bar needs before it can carry its own chance over it. */
	const FIGURE_ROOM = 44;
	/** What an outcome mark needs before the marks beside it start to touch. */
	const MARK_ROOM = 32;

	/** The intervals a run is marked at, coarsening until the marks fit. */
	const MARK_STEPS = [1, 2, 5, 10, 20, 50, 100];

	const bars = $derived(outcomes(distribution).slice(range.first, range.last + 1));

	/** The stretch of the axis the drawn run covers, which every mark is placed against. */
	const span = $derived(axisSpan(distribution, range));

	const tallest = $derived(Math.max(...bars.map(({ probability }) => probability)));

	/** Zero until the drawing has been laid out, which on the server is always. */
	let width = $state(0);

	/** One column of the drawing. The gap is drawn inside it, so this is also the spacing of marks. */
	const column = $derived(bars.length > 0 && width > 0 ? width / bars.length : 0);

	// Unmeasured, a hairline is the usual answer, so it holds one until it knows better.
	const gap = $derived.by(() => {
		if (column === 0) return 1;
		if (column < GAP_FLOOR) return 0;

		return Math.min(Math.round(column / GAP_SHARE), GAP_CEILING);
	});

	/** Whether a bar is wide enough to carry its own chance. Only the detailed view offers one. */
	const figures = $derived(detailed && column >= FIGURE_ROOM);

	// The detailed view reads the bars against a marked axis. In an answer there is no axis, so the
	// tallest bar fills the box it is given.
	const axis = $derived(
		detailed ? axisTicks(tallest) : { top: tallest, step: tallest, values: [] as number[] }
	);

	const expected = $derived(expectedValue(distribution));

	/**
	 * Round values at whatever interval fits, plus the two ends where they would not crowd one, plus
	 * the value the model can never answer with.
	 *
	 * That last one holds no room on the axis and carries no bar, but it is the join the two runs
	 * either side of it meet on and the number a reader reads both against, so it is written under
	 * the join whatever interval the rest of the marks land on.
	 */
	const marks = $derived.by(() => {
		// Measured in whole numbers rather than in bars, because a bar can cover several of them.
		const needed = (column > 0 ? MARK_ROOM / column : 5) * distribution.bucketWidth;
		const step = MARK_STEPS.find((size) => size >= needed) ?? MARK_STEPS.at(-1)!;

		const [first, last] = [bars[0].lowest, bars.at(-1)!.highest];

		const rounds: number[] = [];
		for (let value = Math.ceil(first / step) * step; value <= last; value += step) {
			rounds.push(value);
		}

		const clear = step * 0.75;
		const head = rounds[0] === undefined || rounds[0] - first >= clear ? [first] : [];
		const tail = rounds.at(-1) === undefined || last - rounds.at(-1)! >= clear ? [last] : [];

		const gap = distribution.impossibleValue;
		const join = gap !== null && gap > first && gap < last ? [gap] : [];

		return [...new Set([...head, ...rounds, ...tail, ...join])]
			.sort((first, second) => first - second);
	});

	/** Which outcome is being read, as a position in the answer, or null when none is. */
	let reading = $state<number | null>(null);
	let drawn = $state(false);

	const read = $derived(
		reading !== null && reading >= range.first && reading <= range.last
			? bars[reading - range.first]
			: null
	);

	const percent = (probability: number) => `${(probability * 100).toFixed(1)}%`;

	// The gap is drawn inside a column rather than between two, so a column is exactly a bar's share
	// of the width and a value sits at the same fraction of it however wide the gaps are. Placed off
	// the axis rather than off the value, so a value the model can never answer with takes no room.
	const positionOf = (value: number) =>
		((axisAt(distribution, value) - span.from) / (span.to - span.from)) * 100;

	const within = (value: number) =>
		axisAt(distribution, value) >= span.from && axisAt(distribution, value) <= span.to;

	// A round step is written without a decimal, so an axis climbing in whole percentages reads as
	// whole numbers.
	const tick = (value: number) =>
		`${(value * 100).toFixed(Number.isInteger(axis.step * 100) ? 0 : 1)}%`;

	function readAt(event: PointerEvent) {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
		const index = Math.floor(((event.clientX - box.left) / box.width) * bars.length);

		reading = range.first + Math.min(Math.max(index, 0), bars.length - 1);
	}

	// A touch ends the moment it is lifted, so clearing on that would take the figure away with the
	// finger. It stands until the next touch instead.
	function endRead(event: PointerEvent) {
		if (event.pointerType !== 'touch') reading = null;
	}

	function readByKey(event: KeyboardEvent) {
		const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
		if (step === 0) return;

		event.preventDefault();
		reading = Math.min(
			Math.max((reading ?? outcomeOf(distribution, line)) + step, range.first),
			range.last
		);
	}

	// Once the draw is over the class comes off, so a bar the line brings into range later arrives
	// without replaying it.
	onMount(() => {
		const timer = setTimeout(() => (drawn = true), MOTION_SLOW);

		return () => clearTimeout(timer);
	});
</script>

<figure
	class:detailed
	style="--columns: {bars.length}; --gap: {gap}px; --ticks: {Math.max(axis.values.length - 1, 1)}"
>
	<!-- Reserved whether or not a bar is being read, so the chart never moves under the pointer. -->
	<p class="readout small muted numeric" aria-hidden="true">
		{read ? `${read.label} ${stat}, ${percent(read.probability)}` : ''}
	</p>

	<div class="plot">
		{#if detailed}
			<div class="ticks" aria-hidden="true">
				{#each axis.values as value (value)}
					<span class="micro muted" style="bottom: {(value / axis.top) * 100}%">{tick(value)}</span>
				{/each}
			</div>
		{/if}

		<div class="field">
			<!-- One focusable element, not sixty. What it says is in the label, and the full table sits
			     behind a press in the detailed view. -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
			<div
				class="bars"
				class:drawing={!drawn}
				data-explain="chart"
				role="img"
				aria-label={summary}
				tabindex="0"
				bind:clientWidth={width}
				onpointerdown={readAt}
				onpointermove={readAt}
				onpointerleave={endRead}
				onkeydown={readByKey}
				onblur={() => (reading = null)}
			>
				<!-- A bar the line falls inside is neither over nor under, which is the push colour at
				     every bucket width: at a width of one it is the outcome the line landed on. -->
				{#each bars as bar, index (bar.value)}
					<div class="column">
						{#if figures}
							<span class="value micro muted numeric">{percent(bar.probability)}</span>
						{/if}

						<div
							class="bar"
							class:over={bar.lowest > line}
							class:under={bar.highest < line}
							class:split={bar.lowest <= line && bar.highest >= line}
							class:reading={range.first + index === reading}
							style="height: {(bar.probability / axis.top) * 100}%"
						></div>
					</div>
				{/each}
			</div>

			<!-- What the model expects, in ink, so it is the opposite of the paper in either theme. The
			     label turns back on itself past the middle so a mark near the end is never cut off. -->
			{#if detailed && within(expected)}
				<div class="mark expected" style="left: {positionOf(expected)}%" aria-hidden="true">
					<span class="micro" class:before={positionOf(expected) > 50}>Expected</span>
				</div>
			{/if}

			<!-- The cut the odds are reporting, in the push gold, wherever the chart is drawn. -->
			{#if within(line)}
				<div class="mark chosen" style="left: {positionOf(line)}%" aria-hidden="true"></div>
			{/if}
		</div>

		<div class="marks" aria-hidden="true">
			{#each marks as value (value)}
				<span class="small muted numeric" style="left: {positionOf(value)}%">{value}</span>
			{/each}
		</div>
	</div>
</figure>

<style>
	figure {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-height: 0;
	}

	.readout {
		min-height: var(--space-5);
		text-align: right;
	}

	/*
	 * The bars, and the outcome marks under them. The detailed view adds a gutter for its probability
	 * axis as a first column, and the bars and the marks stay in the last one either way.
	 *
	 * The bars take the whole width where there is no gutter, which is what lets the line handle
	 * beneath be laid out against the same width and land its thumb over the split it makes.
	 */
	.plot {
		display: grid;
		flex: 1;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: minmax(0, 1fr) auto;
		min-height: 0;
	}

	.field {
		position: relative;
		grid-row: 1;
		grid-column: -2;
		min-height: 0;
	}

	.bars {
		display: grid;
		grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
		height: var(--chart-height);
		touch-action: pan-y;
	}

	/* The bar hangs at the bottom of its own column, and the gap is drawn inside the column rather
	   than between two, so a column is exactly a bar's share of the width at every density. That is
	   what lets a mark be placed by its value alone. */
	.column {
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		min-width: 0;
	}

	/* No radius. A rounded bar misreports its own height. */
	.bar {
		flex: none;
		margin-inline: calc(var(--gap) / 2);
		background: var(--chart-neutral);
		transform-origin: bottom;
	}

	.bar.over {
		background: var(--over);
	}

	.bar.under {
		background: var(--under);
	}

	/* The outcome the line cuts through. A colour of its own, because a push is a result rather than
	   the absence of one. */
	.bar.split {
		background: var(--push);
	}

	.bar.reading {
		outline: var(--rule-accent);
	}

	.value {
		text-align: center;
		white-space: nowrap;
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

	/* A vertical mark placed by its value, standing over the bars it cuts between. */
	.mark {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 2px;
		translate: -50%;
		pointer-events: none;
	}

	.mark.chosen {
		background: var(--push);
	}

	.mark.expected {
		background: var(--chart-expected);
	}

	.mark.expected span {
		position: absolute;
		top: 0;
		left: var(--space-1);
		color: var(--chart-expected);
		white-space: nowrap;
	}

	.mark.expected span.before {
		left: auto;
		right: var(--space-1);
	}

	/* The marks are placed by value, so they line up inside the same box the bars are drawn in and
	   the strip has to be told how tall to be. */
	.marks {
		grid-row: 2;
		grid-column: -2;
		position: relative;
		height: var(--space-5);
	}

	.marks span {
		position: absolute;
		transform: translateX(-50%);
		white-space: nowrap;
	}

	/*
	 * The detailed view. It fills the room it is given rather than holding a set height, and the
	 * probability axis takes a gutter of exactly --chart-axis beside the bars, which is the inset the
	 * line handle under it is given so that both are laid out against the same run.
	 */
	.detailed {
		height: 100%;
		min-height: var(--chart-height);
	}

	.detailed .plot {
		grid-template-columns: var(--chart-axis) minmax(0, 1fr);
	}

	.detailed .bars {
		height: 100%;
		border-top: var(--rule);
		/* One hairline per mark, so a bar can be read against the axis beside it. */
		background: repeating-linear-gradient(
			to top,
			var(--hairline) 0 1px,
			transparent 1px calc(100% / var(--ticks))
		);
	}

	.ticks {
		grid-row: 1;
		grid-column: 1;
		position: relative;
		border-right: var(--rule);
	}

	.ticks span {
		position: absolute;
		right: var(--space-2);
		translate: 0 50%;
		white-space: nowrap;
	}

	@media (prefers-reduced-motion: reduce) {
		.drawing .bar {
			animation: none;
		}
	}
</style>
