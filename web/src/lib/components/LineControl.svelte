<!--
	The line, as a handle on the chart's x axis and as a number beside it. See section 10.7.

	The handle travels the drawn run plus three outcomes at each end. The moment the line goes past
	the run, the chart widens to hold it and three more outcomes of headroom open up beyond that, so
	the reader reaches every outcome the model has by dragging alone and the handle is always under
	the bars it is splitting. R10.19 and R10.20.

	Steps of a half. Arrow keys move one step and Page Up and Page Down move five, which a range
	input does not do on its own.
-->
<script lang="ts">
	type Props = {
		line: number;
		/** The outcomes the model can answer with, which is what the field accepts. */
		lowest: number;
		highest: number;
		/** The outcomes the chart draws, which the handle travels with headroom past each end. */
		range: { first: number; last: number };
	};

	let { line = $bindable(), lowest, highest, range }: Props = $props();

	const STEP = 0.5;
	const PAGE_STEPS = 5;

	// The headroom of R10.20. A handle that stops at the edge of the first drawing, and makes the
	// reader type a number to go further, has broken that rule.
	const HEADROOM = 3;

	const travel = $derived({
		first: Math.max(lowest, range.first - HEADROOM),
		last: Math.min(highest, range.last + HEADROOM)
	});

	function onKeydown(event: KeyboardEvent) {
		const direction = event.key === 'PageUp' ? 1 : event.key === 'PageDown' ? -1 : 0;
		if (direction === 0) return;

		event.preventDefault();
		line = Math.min(Math.max(line + direction * STEP * PAGE_STEPS, lowest), highest);
	}
</script>

<div class="control">
	<!-- The travel is written before the value, so a drag that widens the run is never clamped back
	     by the bounds it just outgrew. -->
	<input
		type="range"
		aria-labelledby="line-label"
		min={travel.first}
		max={travel.last}
		step={STEP}
		value={line}
		oninput={(event) => (line = event.currentTarget.valueAsNumber)}
		onkeydown={onKeydown}
	/>

	<div class="field">
		<label class="micro" id="line-label" for="line-number">Line</label>
		<input
			id="line-number"
			type="number"
			class="numeric"
			min={lowest}
			max={highest}
			step={STEP}
			bind:value={line}
		/>
	</div>
</div>

<style>
	.control {
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

	/* Filled accent at --radius-full. Section 10.7, "The line handle". */
	input[type='range']::-webkit-slider-thumb {
		appearance: none;
		width: var(--space-5);
		height: var(--space-5);
		margin-top: calc((var(--space-1) - var(--space-5)) / 2);
		background: var(--accent);
		border-radius: var(--radius-full);
	}

	input[type='range']::-moz-range-thumb {
		width: var(--space-5);
		height: var(--space-5);
		background: var(--accent);
		border: none;
		border-radius: var(--radius-full);
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
