<script lang="ts">
	import { axisAt, axisSpan, axisTicks, expectedValue, outcomeOf, outcomes } from '$lib/odds';

	import type { ChartRange, Distribution } from '$lib/odds';

	type Props = {
		distribution: Distribution;
		/** Name of the predicted stat, in lowercase. */
		stat: string;
		line: number;
		/** Range of outcomes to show. */
		range: ChartRange;
		/** Text description of the chart for screen readers. */
		summary: string;
		/** Detailed view. Adds a probability axis, the expected value and a percentage above each bar. */
		detailed?: boolean;
		/** True if the bars should animate in. */
		animate?: boolean;
	};

	let { distribution, stat, line, range, summary, detailed = false, animate = true }: Props = $props();

	// The sizes below are in pixels and are compared against the width of one column.

	/** Columns narrower than this get no gap between bars. */
	const GAP_FLOOR = 6;
	/** The gap is the column width divided by this. */
	const GAP_SHARE = 12;
	/** Largest gap between bars. */
	const GAP_CEILING = 6;
	/** Minimum column width for showing a percentage above each bar. */
	const FIGURE_ROOM = 44;
	/** Minimum space an axis label needs so labels do not overlap. */
	const MARK_ROOM = 32;

	/** Possible intervals between axis labels. The smallest one that fits is used. */
	const MARK_STEPS = [1, 2, 5, 10, 20, 50, 100];

	const bars = $derived(outcomes(distribution).slice(range.first, range.last + 1));

	const span = $derived(axisSpan(distribution, range));

	const tallest = $derived(Math.max(...bars.map(({ probability }) => probability)));

	/** Chart width in pixels. Zero until it is measured, and always zero on the server. */
	let width = $state(0);

	/** Width of one column, including its gap. */
	const column = $derived(bars.length > 0 && width > 0 ? width / bars.length : 0);

	const gap = $derived.by(() => {
		if (column === 0) return 1;
		if (column < GAP_FLOOR) return 0;

		return Math.min(Math.round(column / GAP_SHARE), GAP_CEILING);
	});

	/** True if the bars are wide enough to show a percentage above each one. */
	const figures = $derived(detailed && column >= FIGURE_ROOM);

	const axis = $derived(
		detailed ? axisTicks(tallest) : { top: tallest, step: tallest, values: [] as number[] }
	);

	const expected = $derived(expectedValue(distribution));

	/** Axis labels. Round numbers at the chosen interval, plus both ends and the impossible value if there is one. */
	const marks = $derived.by(() => {
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

	/** Index of the outcome being hovered or focused, or null if there is none. */
	let reading = $state<number | null>(null);

	const read = $derived(
		reading !== null && reading >= range.first && reading <= range.last
			? bars[reading - range.first]
			: null
	);

	const percent = (probability: number) => `${(probability * 100).toFixed(1)}%`;

	const positionOf = (value: number) =>
		((axisAt(distribution, value) - span.from) / (span.to - span.from)) * 100;

	const within = (value: number) =>
		axisAt(distribution, value) >= span.from && axisAt(distribution, value) <= span.to;

	const tick = (value: number) =>
		`${(value * 100).toFixed(Number.isInteger(axis.step * 100) ? 0 : 1)}%`;

	function readAt(event: PointerEvent) {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
		const index = Math.floor(((event.clientX - box.left) / box.width) * bars.length);

		reading = range.first + Math.min(Math.max(index, 0), bars.length - 1);
	}

	// On touch, the value stays shown until the next touch.
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

</script>

<figure
	class:detailed
	style="--columns: {bars.length}; --gap: {gap}px; --ticks: {Math.max(axis.values.length - 1, 1)}"
>
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
			<!-- The whole chart is one focusable element, not one per bar. -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
			<div
				class="bars"
				class:drawing={animate}
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
							style="height: {(bar.probability / axis.top) * 100}%; --arrival-order: {index}"
						></div>
					</div>
				{/each}
			</div>

			{#if detailed && within(expected)}
				<div class="mark expected" style="left: {positionOf(expected)}%" aria-hidden="true">
					<span class="micro" class:before={positionOf(expected) > 50}>Expected</span>
				</div>
			{/if}

			{#if within(line)}
				<div class="mark chosen" style="left: {positionOf(line)}%" aria-hidden="true">
					<span class="micro" class:before={positionOf(line) > 50}>Line</span>
				</div>
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

	.column {
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		min-width: 0;
	}

	/* No border radius. Rounded corners would misrepresent a bar's height. */
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

	.drawing .bar {
		animation: arrive var(--motion) var(--ease-in)
			calc(var(--arrival-order) * var(--answer-bar-stagger)) backwards;
	}

	@keyframes arrive {
		from {
			opacity: 0.35;
			transform: scaleY(0);
			filter: brightness(1.7) saturate(0.7);
		}

		to {
			opacity: 1;
			transform: scaleY(1);
			filter: none;
		}
	}

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

	.mark span {
		position: absolute;
		top: 0;
		left: var(--space-1);
		white-space: nowrap;
	}

	.mark span.before {
		left: auto;
		right: var(--space-1);
	}

	.mark.expected span {
		color: var(--chart-expected);
	}

	.mark.chosen span {
		color: var(--push);
	}

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

	/* The detailed view. */
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
