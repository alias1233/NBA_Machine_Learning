<!--
	The models a family holds, printed as an index.

	Every model is on the page at once and nothing is hidden behind a control, which is what a reader
	deciding whether to trust a family needs. A family holds fourteen of them, so they are set as rows
	of a printed index rather than as fourteen identical cards: a name, what it answers, and a rule
	between. Opening a row shows what that model measured on games it never saw while it was fitted.

	The figures are not on the page. Opening a row is what asks for that one model's, so a reader who
	opens none costs the service nothing, and what has been fetched is kept for the rest of the visit
	rather than asked for again. The row itself says it is reading while they are on their way, and
	the panel opens on the figures rather than ahead of them.

	Every figure is read against the baseline beside it, and the panel says which of the two won it: a
	drawn check against the better of the pair, in the same green a chart reads an over in, and the word
	in the row's own heading for anybody who cannot see the mark. Which direction counts as better is
	the model's own to say, because on some of these figures a smaller number is the good one. A measure
	the baseline could not be scored on has no winner, and neither does a tie.
-->
<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';

	import { figure, winner } from '$lib/model-evaluation';
	import type { FamilyInfoModel, ModelEvaluation } from '$lib/types';

	type Props = {
		models: FamilyInfoModel[];
		/** The family these models belong to, which is half of what names one to the service. */
		family: string;
	};

	let { models, family }: Props = $props();

	let opened = $state<FamilyInfoModel | null>(null);
	let dialog = $state<HTMLDialogElement>();

	/**
	 * What each opened model measured, by model name.
	 *
	 * A name is in here once its fetch has finished. Null is a model that has never been scored, and
	 * 'unreachable' is a fetch that did not come back. A reader is told which of the two it is,
	 * because only one of them is worth trying again.
	 */
	const scores = new SvelteMap<string, ModelEvaluation | null | 'unreachable'>();
	/** The model whose figures are on their way, which is the one row saying it is being read. */
	let loading = $state<string | null>(null);

	const measured = $derived(opened ? (scores.get(opened.name) ?? null) : null);
	const unreachable = $derived(measured === 'unreachable');
	const scored = $derived(measured === 'unreachable' ? null : measured);

	// The dialog is only in the page while a model is open, so mounting it is what opening means.
	$effect(() => {
		if (dialog && !dialog.open) dialog.showModal();
	});

	/**
	 * Reads what a model measured, and opens on it once it is there.
	 *
	 * The figures are what the panel is for, so it waits for them rather than opening on a line
	 * saying it is working and then growing under the reader. The row that was pressed says it is
	 * reading instead, which is where the reader is looking.
	 */
	async function open(model: FamilyInfoModel) {
		if (scores.has(model.name)) {
			opened = model;
			return;
		}

		if (loading === model.name) return;

		loading = model.name;

		const query = new URLSearchParams({ family, model: model.name });
		const response = await fetch(`/api/evaluations?${query}`).catch(() => null);

		scores.set(model.name, response?.ok ? await response.json() : 'unreachable');

		// A row pressed while this one was on its way owns the panel now.
		if (loading !== model.name) return;

		loading = null;
		opened = model;
	}

	const day = (date: string) => new Date(`${date}T00:00:00`).toLocaleDateString();
</script>

<ul class="index">
	{#each models as model (model.name)}
		<li>
			<button
				type="button"
				class="entry"
				aria-busy={loading === model.name || undefined}
				onclick={() => open(model)}
			>
				<span class="name type-h3">{model.title}</span>
				<span class="what small muted">{model.description}</span>

				<!-- While the figures are on their way the row says so, because the press has to be
				     answered somewhere and this is where the reader is looking. -->
				{#if loading === model.name}
					<span class="state"><span class="tag micro">Loading metrics…</span></span>
				{:else if !model.published}
					<span class="state"><span class="tag micro">Not published yet</span></span>
				{/if}
			</button>
		</li>
	{/each}
</ul>

{#if opened}
	<!-- Named by the model it is about, so a reader who cannot see the panel is told what opened. -->
	<dialog bind:this={dialog} aria-labelledby="opened-model" onclose={() => (opened = null)}>
		<header>
			<div>
				<h3 id="opened-model">{opened.title}</h3>
				<p class="small muted">Evaluation metrics</p>
			</div>
			<button type="button" class="button button--quiet" onclick={() => dialog?.close()}>
				Close
			</button>
		</header>

		{#if unreachable}
			<p class="small muted">What this model measured could not be read. Try again in a moment.</p>
		{:else if !scored}
			<p class="small muted">This model has not been scored yet.</p>
		{:else}
			<!-- Held out is spelled out rather than named, because it is the whole reason the figures
			     below mean anything and the reader is meeting the idea for the first time. -->
			<p class="small muted">
				Scored on {scored.samples.toLocaleString()} held out games the model never saw during 
				training, from {day(scored.first_game)} to {day(scored.last_game)}. Baseline is what answering
				with the season's usual spread of outcomes scores on those same games.
			</p>

			<table class="small numeric">
				<thead>
					<tr>
						<th scope="col">Measure</th>
						<th scope="col">Model</th>
						<th scope="col">Baseline</th>
					</tr>
				</thead>
				<tbody>
					{#each scored.metrics as metric (metric.key)}
						{@const better = winner(metric)}
						<tr>
							<th scope="row">
								{metric.label}
								<!-- Said in the row's own heading, so the winner is carried by words as well as by
								     the mark beside the figure. -->
								{#if better}
									<span class="visually-hidden">
										{better === 'model' ? 'The model is better here.' : 'The baseline is better here.'}
									</span>
								{/if}
								<span class="small muted">{metric.description}</span>
							</th>
							<td>
								<span class="read" class:won={better === 'model'}>
									{figure(metric.value, metric.unit)}
									{#if better === 'model'}{@render check()}{/if}
								</span>
							</td>
							<!-- Words rather than a dash, because a reader should never have to read a
							     punctuation mark to learn that nothing was scored here. -->
							<td>
								{#if metric.floor === null}
									Not scored
								{:else}
									<span class="read" class:won={better === 'baseline'}>
										{figure(metric.floor, metric.unit)}
										{#if better === 'baseline'}{@render check()}{/if}
									</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</dialog>
{/if}

<!-- Drawn rather than typed, in the one stroke weight every mark on this site is drawn in. -->
{#snippet check()}
	<svg class="check" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M4.5 13 10 18.5 19.5 6" />
	</svg>
{/snippet}

<style>
	/* An index, not a grid. Rows in two runs once there is room for two, which is where a family of
	   fourteen stops being a column a reader has to scroll and becomes a page they can take in. */
	.index {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
		border-top: var(--rule-panel);
	}

	.index > li {
		border-bottom: var(--rule-panel);
	}

	/* The name, then what it answers, then whatever state it is in. A whole row is the control, so it
	   holds the row's own padding and carries none of the platform's button chrome. */
	.entry {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: baseline;
		column-gap: var(--space-4);
		row-gap: var(--space-1);
		width: 100%;
		min-height: var(--tap-target);
		padding: var(--space-3) var(--space-2);
		background: none;
		border: none;
		font: inherit;
		text-align: start;
		cursor: pointer;
		transition: background var(--motion-fast) var(--ease-in);
	}

	.entry:hover,
	.entry:focus-visible {
		background: var(--panel);
	}

	.entry:hover .name {
		color: var(--accent);
	}

	.what {
		grid-column: 1;
	}

	.state {
		grid-area: 1 / 2 / span 2 / 3;
		align-self: center;
	}

	dialog {
		max-width: min(100%, var(--control-column));
		padding: var(--space-5);
		background: var(--surface);
		color: var(--ink);
		border: var(--rule-panel);
		border-radius: var(--radius);
	}

	dialog::backdrop {
		background: light-dark(rgb(28 26 22 / 0.4), rgb(0 0 0 / 0.6));
	}

	dialog header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		margin-block-end: var(--space-3);
	}

	table {
		width: 100%;
		margin-block-start: var(--space-4);
		border-collapse: collapse;
		text-align: start;
	}

	th,
	td {
		padding: var(--space-2);
		vertical-align: top;
		text-align: start;
	}

	/* A figure and, where it won, the mark that says so. The mark hangs off the end of the figure
	   rather than in a column of its own, so a row stays as wide as its two numbers. */
	.read {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		white-space: nowrap;
	}

	/* The better of the pair, marked the way the site marks an over: green, and never green alone. The
	   figure also takes full-strength ink and the row says which side won it in words. */
	.read.won {
		color: var(--over);
		font-weight: 600;
	}

	.check {
		width: 0.9375rem;
		height: 0.9375rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 2.5;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	/* The label and the sentence saying what it means, stacked, so the row stays two columns wide. */
	tbody th span {
		display: block;
		font-weight: normal;
	}

	@media (min-width: 48rem) {
		.index {
			grid-template-columns: 1fr 1fr;
			column-gap: var(--space-6);
		}
	}
</style>
