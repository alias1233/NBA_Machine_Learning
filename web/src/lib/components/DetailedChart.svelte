<!--
	The chart at the size it deserves, over the whole screen.

	It is the same drawing as the one in the answer, given the room to show every outcome at once, a
	probability axis to read them against and a mark for what the model expects. The line and the odds
	come with it, because the chart, the line and the odds are one object wherever they are drawn. The
	odds sit at the end of the line's own row and are set larger, because here they are read from
	across a screen.

	The exact figures sit behind one disclosure at the top, beside what the model expects. It opens as
	a panel over the drawing, so nothing else in the view moves, and it holds every outcome ordered
	either by value or by chance, which is the ranking a reader wants when they want one.

	A modal dialog, so the reader is inside it until they leave: Escape closes an open panel and then
	the view, focus stays within it, and the page underneath it holds still and comes back where it was.
-->
<script lang="ts">
	import DistributionChart from '$lib/components/DistributionChart.svelte';
	import LineControl from '$lib/components/LineControl.svelte';
	import OddsReadout from '$lib/components/OddsReadout.svelte';
	import { sentenceCase } from '$lib/models';
	import { appear } from '$lib/motion';
	import {
		calculateOdds,
		expectedValue,
		mostLikelyOutcomes,
		oddsPercentages,
		outcomes
	} from '$lib/odds';

	import type { Distribution } from '$lib/odds';

	type Props = {
		distribution: Distribution;
		/** What the model predicts, lowercase. */
		stat: string;
		/** What the answer names itself: the player and the stat, then the game. */
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

	/** Whether the table of every outcome stands over the drawing. */
	let showing = $state(false);

	/** What that table is ordered by. Value is the order the outcomes come in. */
	let sort = $state<'value' | 'chance'>('value');

	/** Every outcome the model can answer with, because this view holds the whole answer. */
	const range = $derived({ first: 0, last: distribution.probabilities.length - 1 });

	const expected = $derived(expectedValue(distribution));
	const likeliest = $derived(mostLikelyOutcomes(distribution, 1)[0]);

	// Ordered by chance is the ranking, so one table answers both questions the reader can ask of it.
	const rows = $derived(
		sort === 'chance'
			? mostLikelyOutcomes(distribution, distribution.probabilities.length)
			: outcomes(distribution)
	);

	const odds = $derived(calculateOdds(distribution, line));
	const spoken = $derived(oddsPercentages(odds));

	const summary = $derived(
		[
			`Expected ${expected.toFixed(1)} ${stat}.`,
			`Most likely ${likeliest.label} ${stat}.`,
			`Over ${line}, ${spoken.over} percent.`,
			`Under ${line}, ${spoken.under} percent.`,
			`Push ${line}, ${spoken.push} percent.`
		].join(' ')
	);

	const percent = (probability: number) => `${(probability * 100).toFixed(1)}%`;

	// The panel over the drawing is the innermost thing open, so it is what Escape leaves first.
	function onKeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape' || !showing) return;

		event.preventDefault();
		showing = false;
	}

	// A press anywhere but the panel and the control that opened it puts it away, which is how a thing
	// floating over something else is dismissed.
	$effect(() => {
		if (!showing) return;

		const away = ({ target }: PointerEvent) => {
			const pressed = target as Node;

			if (!sheet?.contains(pressed) && !toggle?.contains(pressed)) showing = false;
		};

		document.addEventListener('pointerdown', away);

		return () => document.removeEventListener('pointerdown', away);
	});

	// It is only ever in the page while it is open, so opening it is what mounting it means. The way
	// out takes the focus, rather than whichever control happens to be written first.
	$effect(() => {
		if (dialog && !dialog.open) {
			dialog.showModal();
			closer?.focus();
		}
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

			<!-- What the model expects and the way to the exact figures, together, because both are the
			     answer read as numbers rather than as a drawing. -->
			<div class="tools">
				<dl class="facts">
					<div>
						<dt class="micro muted">Expected</dt>
						<dd class="figure">{expected.toFixed(1)}</dd>
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

		<!-- The handle is inset by the gutter the probability axis takes and is given the whole width
		     under the run, so it is laid out against the bars rather than against the view. -->
		<div class="handle">
			<LineControl id="line-detailed" bind:line {distribution} {range}>
				<OddsReadout {odds} large />
			</LineControl>
		</div>

		<!--
			Written after the control that opens it, so it follows it for a reader moving by keyboard,
			and placed over the drawing by the grid rather than by its position in the page. It takes
			the room its own contents need and no more.
		-->
		{#if showing}
			<div bind:this={sheet} id={SHEET} class="panel sheet" transition:appear>
				<h3>All outcomes</h3>

				<div class="sheet-body">
					<table class="small numeric">
						<thead>
							<tr>
								<!-- The headings are the ordering, so the table is read and reordered in one
								     place rather than carrying a control above it. -->
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
	/*
	 * The whole screen, on the surface plane, because the chart is a data area and data is drawn on
	 * page-side ground wherever it sits. It leaves the top layer the moment it closes, so it is given
	 * a place above the header to close from.
	 */
	dialog {
		position: fixed;
		inset: 0;
		z-index: 40;
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

	/* It rises over the page rather than appearing on top of it. */
	@starting-style {
		dialog[open] {
			opacity: 0;
		}
	}

	dialog::backdrop {
		background: none;
	}

	/* The chart takes whatever the words above and the controls below leave it, and never falls under
	   the height it is drawn at in an answer. Every row is placed rather than flowed, because the
	   chart and the panel that opens over it share one cell. */
	.view {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: auto minmax(var(--chart-height), 1fr) auto;
		gap: var(--space-4);
		height: 100%;
		padding: var(--space-5) var(--space-4);
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

	/* Fixed width, so a figure of a different length never moves the controls beside it. */
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

	/* One column at every width. The handle has to be laid out against the same width the bars are,
	   so nothing shares its row. */
	.handle {
		grid-area: 3 / 1;
		padding-left: var(--chart-axis);
	}

	/*
	 * A panel over the drawing, in the same grid cell, so opening one moves nothing else in the view.
	 * It floats above the page, so it is one of the few things on the site carrying a shadow. It hangs
	 * from the end the control that opened it sits at and is only as wide as what it holds, because
	 * two columns of figures spread across a screen are harder to read across, not easier.
	 */
	.sheet {
		grid-area: 2 / 1;
		/* Raised over the drawing rather than merely later than it. The chart places its own marks,
		   and a positioned thing is painted above every plain background whatever the order. */
		position: relative;
		z-index: 1;
		/* It takes the room its own contents need and no more, up to the whole drawing, so a short
		   run is a short panel and sixty rows are a scrolling one. */
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

	/* The heading is the control, so it reads as the heading and behaves as a button. */
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

	/* Current colour, a stroke and no fill, at the size of the word beside it. */
	th svg {
		flex: none;
		width: 1em;
		height: 1em;
	}

	@media (min-width: 40rem) {
		.view {
			padding-inline: var(--space-5);
		}
	}
</style>
