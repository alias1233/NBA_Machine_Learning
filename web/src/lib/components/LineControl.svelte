<script lang="ts">
	import { axisAt, axisSpan, valueAt } from '$lib/odds';

	import type { Snippet } from 'svelte';
	import type { ChartRange, Distribution } from '$lib/odds';

	type Props = {
		/** Must be unique on the page. */
		id: string;
		line: number;
		distribution: Distribution;
		/** Range of outcomes the chart shows. Sets the limits for both controls. */
		range: ChartRange;
		/** Rendered at the end of the field row. */
		children?: Snippet;
	};

	let { id, line = $bindable(), distribution, range, children }: Props = $props();

	const STEP = 0.5;
	const PAGE_STEPS = 5;

	const width = $derived(distribution.bucketWidth);

	const span = $derived(axisSpan(distribution, range));

	// Centers of the first and last bars shown.
	const drawn = $derived({ first: span.from + width / 2, last: span.to - width / 2 });
	const columns = $derived(range.last - range.first + 1);

	const reach = $derived({
		lowest: valueAt(distribution, drawn.first),
		highest: valueAt(distribution, drawn.last)
	});

	const nearest = (axis: number) =>
		valueAt(
			distribution,
			Math.min(Math.max(Math.round(axis / STEP) * STEP, drawn.first), drawn.last)
		);

	let field = $state<HTMLInputElement>();

	/** True while the user is typing in the field, so the line does not overwrite it. */
	let typing = $state(false);

	function move(steps: number) {
		typing = false;
		line = nearest(axisAt(distribution, line) + steps * STEP);
	}

	// svelte-ignore state_referenced_locally
	const opening = String(line);

	// Keeps the field in sync with the line, except while the user is typing.
	$effect(() => {
		const settled = String(line);

		if (field && !typing) field.value = settled;
	});

	// The field handles arrow keys itself, because native stepping stops on values the slider skips.
	const HANDLE_KEYS: Record<string, number> = { PageUp: PAGE_STEPS, PageDown: -PAGE_STEPS };
	const FIELD_KEYS: Record<string, number> = { ArrowUp: 1, ArrowDown: -1, ...HANDLE_KEYS };

	const stepping = (keys: Record<string, number>) => (event: KeyboardEvent) => {
		const steps = keys[event.key];

		if (steps === undefined) return;

		event.preventDefault();
		move(steps);
	};

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

	/* Stretched so the thumb's centre sits over the middle of the first and last bars. */
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
		width: calc(var(--space-8) * 1.25);
	}
</style>
