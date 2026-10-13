<script lang="ts">
	import DistributionChart from '$lib/components/DistributionChart.svelte';
	import LineControl from '$lib/components/LineControl.svelte';
	import OddsReadout from '$lib/components/OddsReadout.svelte';
	import { sentenceCase } from '$lib/models';
	import { appear } from '$lib/motion';
	import {
		calculateOdds,
		expectedValue,
		figureText,
		mostLikelyOutcomes,
		oddsPercentages,
		outcomes
	} from '$lib/odds';

	import type { Distribution } from '$lib/odds';

	type Props = {
		distribution: Distribution;
		/** Name of the predicted stat, in lowercase. */
		stat: string;
		heading: string;
		subheading: string;
		line: number;
		onclose: () => void;
	};

	let { distribution, stat, heading, subheading, line = $bindable(), onclose }: Props = $props();

	const TITLE = 'detailed-chart-title';
	const SHEET = 'detailed-chart-outcomes';

	let dialog = $state<HTMLDialogElement>();
	let closer = $state<HTMLButtonElement>();
	let sheet = $state<HTMLElement>();
	let toggle = $state<HTMLButtonElement>();

	/** True when the table of all outcomes is shown over the chart. */
	let showing = $state(false);

	let sort = $state<'value' | 'chance'>('value');

	const range = $derived({ first: 0, last: distribution.probabilities.length - 1 });

	const expected = $derived(expectedValue(distribution));
	const expectedText = $derived(figureText(distribution, expected));
	const likeliest = $derived(mostLikelyOutcomes(distribution, 1)[0]);

	const rows = $derived(
		sort === 'chance'
			? mostLikelyOutcomes(distribution, distribution.probabilities.length)
			: outcomes(distribution)
	);

	const odds = $derived(calculateOdds(distribution, line));
	const spoken = $derived(oddsPercentages(odds));

	const summary = $derived(
		[
			`Expected ${expectedText} ${stat}.`,
			`Most likely ${likeliest.label} ${stat}.`,
			`Under ${line}, ${spoken.under} percent.`,
			`Push ${line}, ${spoken.push} percent.`,
			`Over ${line}, ${spoken.over} percent.`
		].join(' ')
	);

	const percent = (probability: number) => `${(probability * 100).toFixed(1)}%`;

	function onKeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape' || !showing) return;

		event.preventDefault();
		showing = false;
	}

	$effect(() => {
		if (!showing) return;

		const away = ({ target }: PointerEvent) => {
			const pressed = target as Node;

			if (!sheet?.contains(pressed) && !toggle?.contains(pressed)) showing = false;
		};

		document.addEventListener('pointerdown', away);

		return () => document.removeEventListener('pointerdown', away);
	});

	$effect(() => {
		if (dialog && !dialog.open) {
			dialog.showModal();
			closer?.focus();
		}
	});

	/** Not reactive. Only stores the value from the last run of the effect. */
	let wasShowing = false;

	// Moves focus to the panel when it opens and back to the toggle when it closes.
	$effect(() => {
		if (showing) sheet?.focus({ preventScroll: true });
		else if (wasShowing) toggle?.focus({ preventScroll: true });

		wasShowing = showing;
	});
</script>

<dialog bind:this={dialog} aria-labelledby={TITLE} onclose={onclose} onkeydown={onKeydown}>
	<div class="view">
		<header class="head">
			<div class="named">
				<h2 id={TITLE} class="type-h2">{heading}</h2>
				{#if subheading}
					<p class="small muted">{subheading}</p>
				{/if}
			</div>

			<div class="tools">
				<dl class="facts">
					<div>
						<dt class="micro muted">Expected</dt>
						<dd class="figure">{expectedText}</dd>
					</div>
				</dl>

				<button
					bind:this={toggle}
					type="button"
					class="button button--quiet"
					aria-expanded={showing}
					aria-controls={SHEET}
					onclick={() => (showing = !showing)}
				>
					All outcomes
				</button>

				<button bind:this={closer} type="button" class="button" onclick={() => dialog?.close()}>
					Close
				</button>
			</div>
		</header>

		<div class="drawing">
			<DistributionChart detailed {distribution} {stat} {line} {range} {summary} />
		</div>

		<div class="handle">
			<LineControl id="line-detailed" bind:line {distribution} {range}>
				<OddsReadout {odds} large />
			</LineControl>
		</div>

		{#if showing}
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<div bind:this={sheet} id={SHEET} class="panel sheet" tabindex="-1" transition:appear>
				<h3>All outcomes</h3>

				<div class="sheet-body">
					<table class="small numeric">
						<thead>
							<tr>
								<th scope="col" aria-sort={sort === 'value' ? 'ascending' : 'none'}>
									<button type="button" onclick={() => (sort = 'value')}>
										{sentenceCase(stat)}
										{#if sort === 'value'}
											<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
												<path d="M8 12.5V4M4.5 7.5 8 4l3.5 3.5" />
											</svg>
										{/if}
									</button>
								</th>

								<th scope="col" aria-sort={sort === 'chance' ? 'descending' : 'none'}>
									<button type="button" onclick={() => (sort = 'chance')}>
										Chance
										{#if sort === 'chance'}
											<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
												<path d="M8 3.5V12M4.5 8.5 8 12l3.5-3.5" />
											</svg>
										{/if}
									</button>
								</th>
							</tr>
						</thead>
						<tbody>
							{#each rows as outcome (outcome.value)}
								<tr>
									<td>{outcome.label}</td>
									<td>{percent(outcome.probability)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		position: fixed;
		inset: 0;
		z-index: var(--layer-overlay);
		width: auto;
		max-width: none;
		height: auto;
		max-height: none;
		margin: 0;
		padding: 0;
		overflow: hidden;
		background: var(--surface);
		color: var(--ink);
		border: none;
		opacity: 1;
		transition: opacity var(--motion) var(--ease-in);
	}

	@starting-style {
		dialog[open] {
			opacity: 0;
		}
	}

	dialog::backdrop {
		background: none;
	}

	.view {
		--view-gutter: var(--space-4);

		display: grid;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: auto minmax(var(--chart-height), 1fr) auto;
		gap: var(--space-4);
		height: 100%;
		padding: var(--space-5) var(--view-gutter);
		overflow-y: auto;
	}

	.head {
		grid-area: 1 / 1;
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-4) var(--space-6);
	}

	.tools {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-4);
	}

	.facts {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: var(--figure-column);
	}

	.facts dd {
		margin: var(--space-1) 0 0;
		white-space: nowrap;
	}

	.drawing {
		grid-area: 2 / 1;
		min-height: 0;
	}

	.handle {
		grid-area: 3 / 1;
		padding-left: var(--chart-axis);
	}

	.sheet {
		grid-row: 2 / -1;
		grid-column: 1;
		position: relative;
		z-index: 1;
		align-self: start;
		justify-self: end;
		width: max-content;
		max-width: 100%;
		max-height: 100%;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		min-height: 0;
		box-shadow: var(--shadow);
	}

	.sheet-body {
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior: contain;
		padding-right: var(--space-5);
	}

	table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
	}

	th,
	td {
		padding: var(--space-1) var(--space-5) var(--space-1) 0;
		border-bottom: var(--rule-panel);
	}

	th:last-child,
	td:last-child {
		padding-right: 0;
		text-align: right;
	}

	th {
		position: sticky;
		top: 0;
		padding: 0;
		background: var(--panel);
		color: var(--ink-muted);
		font-weight: 600;
	}

	th button {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		min-height: var(--tap-target);
		padding: 0 var(--space-5) 0 0;
		background: none;
		border: none;
		color: inherit;
		font: inherit;
		text-align: inherit;
		cursor: pointer;
	}

	th:last-child button {
		justify-content: flex-end;
		padding-right: 0;
	}

	th button:hover {
		color: var(--ink);
	}

	th svg {
		flex: none;
		width: 1em;
		height: 1em;
	}

	@media (width < 40rem) {
		.drawing,
		.handle {
			margin-left: calc(var(--view-gutter) * -1);
		}
	}

	@media (min-width: 40rem) {
		.view {
			--view-gutter: var(--space-5);
		}
	}
</style>
