<!--
	The line, as a handle on the chart's x axis and as a number beside it.

	The handle travels exactly the drawn run. Its thumb is laid out to put it over the split it makes,
	and the field accepts that same run. The detailed view draws every outcome, so its control reaches
	every outcome without changing these rules.

	Steps of a half, whatever the model's outcomes are worth. A line is a question a reader asks, not
	something the answer's shape decides, so it moves in halves even where one bar covers three
	points. Arrow keys move one step and Page Up and Page Down move five, which a range input does not
	do on its own.

	The field takes only what the handle can reach. A typed number settles on the nearest of those and
	the field's own keys step along the same run, so the two controls read the same value at every
	press and no number the chart stands behind nothing for is ever asked about.

	Where the model names a value it can never answer with, the handle steps straight over it and
	settles on it, because every line either side of it asks the same question and that value is the
	plainest way to write it.

	Whatever the line settles at goes at the far end of the field's own row, so the control and what
	it decides sit at the two ends of one line under the chart.
-->
<script lang="ts">
	import { axisAt, axisSpan, valueAt } from '$lib/odds';

	import type { Snippet } from 'svelte';
	import type { ChartRange, Distribution } from '$lib/odds';

	type Props = {
		/** Unique on the page. The chart is drawn twice once the detailed view is open. */
		id: string;
		line: number;
		/** The answer being read, which says what the field accepts and how wide one bar is. */
		distribution: Distribution;
		/** The outcomes the chart draws, which set the limits for both controls. */
		range: ChartRange;
		/** What the line settles at, or the way to read it larger. Sits at the end of the field row. */
		children?: Snippet;
	};

	let { id, line = $bindable(), distribution, range, children }: Props = $props();

	const STEP = 0.5;
	const PAGE_STEPS = 5;

	const width = $derived(distribution.bucketWidth);

	// The handle travels the axis rather than the values, so its thumb tracks the bars even where the
	// model names a value it can never answer with and the two are not the same run.
	const span = $derived(axisSpan(distribution, range));

	// The middle of the first and last bars drawn. The handle is laid out against bar middles, because
	// that is what its thumb has to line up with.
	const drawn = $derived({ first: span.from + width / 2, last: span.to - width / 2 });
	const columns = $derived(range.last - range.first + 1);

	/** The two ends of everything the handle can settle on, so the field offers exactly that run. */
	const reach = $derived({
		lowest: valueAt(distribution, drawn.first),
		highest: valueAt(distribution, drawn.last)
	});

	/** The nearest line the handle could have been dragged to, which is where any other one settles. */
	const nearest = (axis: number) =>
		valueAt(
			distribution,
			Math.min(Math.max(Math.round(axis / STEP) * STEP, drawn.first), drawn.last)
		);

	let field = $state<HTMLInputElement>();

	/** True while the box holds words the reader is still typing, which the line must not write over. */
	let typing = $state(false);

	/** Moves the line along the axis, which is the only run either control travels. */
	function move(steps: number) {
		// A step is the line moving rather than the reader typing, so the box takes the new one.
		typing = false;
		line = nearest(axisAt(distribution, line) + steps * STEP);
	}

	// What the box opens holding. Written once, for the server's markup and the first paint, and the
	// effect below owns it from then on.
	// svelte-ignore state_referenced_locally
	const opening = String(line);

	/**
	 * The box follows the line, except while the reader is typing in it.
	 *
	 * Writing into a field under a caret puts the caret back to the front of it. A number typed a
	 * digit at a time settles the line at every keystroke, so a box following it would be rewritten
	 * under the reader and the next digit would land at the wrong end. Leaving the box hands it back,
	 * which is also what puts an emptied or half typed one right.
	 */
	$effect(() => {
		const settled = String(line);

		if (field && !typing) field.value = settled;
	});

	// How many steps a key is worth on each control. The handle moves one step on an arrow already, so
	// it takes only the pages. The field's own arrows count in halves from its minimum, which stops on
	// the numbers the handle steps over, so it takes both and moves along the axis instead.
	const HANDLE_KEYS: Record<string, number> = { PageUp: PAGE_STEPS, PageDown: -PAGE_STEPS };
	const FIELD_KEYS: Record<string, number> = { ArrowUp: 1, ArrowDown: -1, ...HANDLE_KEYS };

	const stepping = (keys: Record<string, number>) => (event: KeyboardEvent) => {
		const steps = keys[event.key];

		if (steps === undefined) return;

		event.preventDefault();
		move(steps);
	};

	// A part typed number reads as nothing, so it is left alone until there is something to settle.
	function onFieldInput(event: Event & { currentTarget: HTMLInputElement }) {
		typing = true;

		const typed = event.currentTarget.valueAsNumber;

		if (Number.isNaN(typed)) return;

		line = nearest(axisAt(distribution, typed));
	}
</script>

<div class="control" style="--columns: {columns}">
	<input
		type="range"
		class="aligned"
		aria-labelledby="{id}-label"
		min={drawn.first}
		max={drawn.last}
		step={STEP}
		value={axisAt(distribution, line)}
		data-explain="line"
		oninput={(event) => (line = valueAt(distribution, event.currentTarget.valueAsNumber))}
		onkeydown={stepping(HANDLE_KEYS)}
	/>

	<div class="row">
		<div class="field">
			<label class="micro" id="{id}-label" for="{id}-number">Line</label>
			<input
				bind:this={field}
				id="{id}-number"
				type="number"
				class="numeric"
				min={reach.lowest}
				max={reach.highest}
				step={STEP}
				value={opening}
				oninput={onFieldInput}
				onblur={() => (typing = false)}
				onkeydown={stepping(FIELD_KEYS)}
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
	 * A range input stops the center of its thumb half a thumb inside each end, and a chart stops the
	 * center of its first bar half a column inside. Stretching the track by a thumb and pulling it
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

	/* Wide enough for the longest line any model can be asked about and no wider, so the row still
	   holds the field and whatever sits at its far end on one line on a phone. */
	input[type='number'] {
		width: calc(var(--space-8) * 1.25);
	}
</style>
