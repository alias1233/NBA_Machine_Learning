<!--
	The line, as a handle on the chart's x axis and as a number beside it.

	The handle travels the drawn run plus three outcomes at each end. The moment the line goes past
	the run, the chart widens to hold it and three more outcomes of headroom open up beyond that, so
	the reader reaches every outcome the model has by dragging alone and the handle is always under
	the bars it is splitting.

	Where the whole run is already drawn there is nothing left to widen into, so the handle travels
	exactly the drawn run and is laid out to put its thumb over the split it makes. That is the
	detailed view, where every outcome is on screen at once.

	Steps of a half, whatever the model's outcomes are worth. A line is a question a reader asks, not
	something the answer's shape decides, so it moves in halves even where one bar covers three
	points. Arrow keys move one step and Page Up and Page Down move five, which a range input does not
	do on its own.

	Whatever the line settles at goes at the far end of the field's own row, so the control and what
	it decides sit at the two ends of one line under the chart.
-->
<script lang="ts">
	import { highestValue, lowestValue, valueSpan } from '$lib/odds';

	import type { Snippet } from 'svelte';
	import type { ChartRange, Distribution } from '$lib/odds';

	type Props = {
		/** Unique on the page. The chart is drawn twice once the detailed view is open. */
		id: string;
		line: number;
		/** The answer being read, which says what the field accepts and how wide one bar is. */
		distribution: Distribution;
		/** The outcomes the chart draws, which the handle travels with headroom past each end. */
		range: ChartRange;
		/** What the line settles at, or the way to read it larger. Sits at the end of the field row. */
		children?: Snippet;
	};

	let { id, line = $bindable(), distribution, range, children }: Props = $props();

	const STEP = 0.5;
	const PAGE_STEPS = 5;

	// A handle that stops at the edge of the first drawing, and makes the reader type a number to go
	// further, cannot reach every outcome by dragging. This is how many outcomes past it it travels.
	const HEADROOM = 3;

	const lowest = $derived(lowestValue(distribution));
	const highest = $derived(highestValue(distribution));

	const width = $derived(distribution.bucketWidth);
	const span = $derived(valueSpan(distribution, range));

	// The middle of the first and last bars drawn, and of the first and last the model has. The
	// handle is laid out against bar middles, because that is what its thumb has to line up with.
	const drawn = $derived({ first: span.from + width / 2, last: span.to - width / 2 });
	const outermost = $derived({ first: lowest + (width - 1) / 2, last: highest - (width - 1) / 2 });

	const travel = $derived({
		first: Math.max(outermost.first, drawn.first - HEADROOM * width),
		last: Math.min(outermost.last, drawn.last + HEADROOM * width)
	});

	// Lining the thumb up with the bars only means anything where it travels exactly the run they are
	// drawn over. Anywhere else it reaches past what is drawn, so there is nothing to line up with.
	const aligned = $derived(travel.first === drawn.first && travel.last === drawn.last);
	const columns = $derived(range.last - range.first + 1);

	function onKeydown(event: KeyboardEvent) {
		const direction = event.key === 'PageUp' ? 1 : event.key === 'PageDown' ? -1 : 0;
		if (direction === 0) return;

		event.preventDefault();
		line = Math.min(Math.max(line + direction * STEP * PAGE_STEPS, lowest), highest);
	}
</script>

<div class="control" style="--columns: {columns}">
	<!-- The travel is written before the value, so a drag that widens the run is never clamped back
	     by the bounds it just outgrew. -->
	<input
		type="range"
		class:aligned
		aria-labelledby="{id}-label"
		min={travel.first}
		max={travel.last}
		step={STEP}
		value={line}
		oninput={(event) => (line = event.currentTarget.valueAsNumber)}
		onkeydown={onKeydown}
	/>

	<div class="row">
		<div class="field">
			<label class="micro" id="{id}-label" for="{id}-number">Line</label>
			<input
				id="{id}-number"
				type="number"
				class="numeric"
				min={lowest}
				max={highest}
				step={STEP}
				bind:value={line}
			/>
		</div>

		{@render children?.()}
	</div>
</div>

<style>
	.control {
		--thumb: var(--space-5);

		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	input[type='range'] {
		width: 100%;
		height: var(--tap-target);
		margin: 0;
		background: none;
		appearance: none;
		cursor: pointer;
	}

	/*
	 * A range input stops the centre of its thumb half a thumb inside each end, and a chart stops the
	 * centre of its first bar half a column inside. Stretching the track by a thumb and pulling it
	 * back by a column is what makes those two the same place, so the thumb sits exactly over the
	 * split it makes. It hangs half a thumb past each end doing so, which the padding of whatever it
	 * sits in absorbs.
	 */
	input.aligned {
		width: calc(100% - 100% / var(--columns) + var(--thumb));
		margin-inline: calc((100% / var(--columns) - var(--thumb)) / 2);
	}

	input[type='range']::-webkit-slider-runnable-track {
		height: var(--space-1);
		background: var(--surface-sunken);
		border-radius: var(--radius-full);
	}

	input[type='range']::-moz-range-track {
		height: var(--space-1);
		background: var(--surface-sunken);
		border-radius: var(--radius-full);
	}

	/* Filled accent at --radius-full. Its width is the one the alignment above is worked out from, so
	   both read the same token and cannot drift apart. */
	input[type='range']::-webkit-slider-thumb {
		appearance: none;
		width: var(--thumb);
		height: var(--thumb);
		margin-top: calc((var(--space-1) - var(--thumb)) / 2);
		background: var(--plane-accent);
		border-radius: var(--radius-full);
	}

	input[type='range']::-moz-range-thumb {
		width: var(--thumb);
		height: var(--thumb);
		background: var(--plane-accent);
		border: none;
		border-radius: var(--radius-full);
	}

	/* The field at one end and whatever was given to sit beside it at the other. Where the two cannot
	   share a line the second drops under the first, rather than running past the edge of a surface
	   that clips it. */
	.row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
	}

	.field {
		flex-direction: row;
		align-items: center;
		gap: var(--space-3);
	}

	input[type='number'] {
		width: calc(var(--space-8) * 1.5);
	}
</style>
