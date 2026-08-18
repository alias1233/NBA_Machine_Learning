<!--
	The models a family holds, printed as an index.

	Every model is on the page at once and nothing is hidden behind a control, which is what a reader
	deciding whether to trust a family needs. A family holds fourteen of them, so they are set as rows
	of a printed index rather than as fourteen identical cards: a name, what it answers, and a rule
	between. Opening a row shows what that model measured on games it never saw while it was fitted.

	The figures are not on the page. Opening a row is what asks for that one model's, so a reader who
	opens none costs the service nothing, and what has been fetched is kept for the rest of the visit
	rather than asked for again.
-->
<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';

	import type { FamilyAboutModel, Metric, ModelEvaluation } from '$lib/types';

	type Props = {
		models: FamilyAboutModel[];
		/** The family these models belong to, which is half of what names one to the service. */
		family: string;
	};

	let { models, family }: Props = $props();

	let opened = $state<FamilyAboutModel | null>(null);
	let dialog = $state<HTMLDialogElement>();

	/**
	 * What each opened model measured, by model name.
	 *
	 * A name is in here once its fetch has finished. Null is a model that has never been scored, and
	 * 'unreachable' is a fetch that did not come back. A reader is told which of the two it is,
	 * because only one of them is worth trying again.
	 */
	const scores = new SvelteMap<string, ModelEvaluation | null | 'unreachable'>();
	let loading = $state<string | null>(null);

	const measured = $derived(opened ? (scores.get(opened.name) ?? null) : null);
	const unreachable = $derived(measured === 'unreachable');
	const scored = $derived(measured === 'unreachable' ? null : measured);
	const fetching = $derived(opened !== null && loading === opened.name);

	// The dialog is only in the page while a model is open, so mounting it is what opening means.
	$effect(() => {
		if (dialog && !dialog.open) dialog.showModal();
	});

	async function open(model: FamilyAboutModel) {
		opened = model;

		if (scores.has(model.name)) return;

		loading = model.name;

		const query = new URLSearchParams({ family, model: model.name });
		const response = await fetch(`/api/evaluations?${query}`).catch(() => null);

		scores.set(model.name, response?.ok ? await response.json() : 'unreachable');
		loading = null;
	}

	/** A figure written the way its unit asks to be read. */
	function figure(value: number, unit: Metric['unit']): string {
		if (unit === 'probability') return `${(value * 100).toFixed(1)}%`;

		return value.toFixed(3);
	}

	const day = (date: string) => new Date(`${date}T00:00:00`).toLocaleDateString();
</script>

<ul class="index">
	{#each models as model (model.name)}
		<li>
			<button type="button" class="entry" onclick={() => open(model)}>
				<span class="name type-h3">{model.title}</span>
				<span class="what small muted">{model.description}</span>

				{#if !model.published}
					<span class="state"><span class="tag micro">Not published yet</span></span>
				{/if}
			</button>
		</li>
	{/each}
</ul>

{#if opened}
	<dialog bind:this={dialog} onclose={() => (opened = null)}>
		<header>
			<h3>{opened.title}</h3>
			<button type="button" class="button button--quiet" onclick={() => dialog?.close()}>
				Close
			</button>
		</header>

		{#if fetching}
			<p class="small muted">Reading what this model measured…</p>
		{:else if unreachable}
			<p class="small muted">What this model measured could not be read. Try again in a moment.</p>
		{:else if !scored}
			<p class="small muted">This model has not been scored yet.</p>
		{:else}
			<!-- Held out is spelled out rather than named, because it is the whole reason the figures
			     below mean anything and the reader is meeting the idea for the first time. -->
			<p class="small muted">
				Scored on {scored.samples.toLocaleString()} games the model never saw while it was being
				built, from {day(scored.first_game)} to {day(scored.last_game)}. Baseline is what answering
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
						<tr>
							<th scope="row">
								{metric.label}
								<span class="small muted">{metric.description}</span>
							</th>
							<td>{figure(metric.value, metric.unit)}</td>
							<!-- Words rather than a dash, because a reader should never have to read a
							     punctuation mark to learn that nothing was scored here. -->
							<td>{metric.floor === null ? 'Not scored' : figure(metric.floor, metric.unit)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</dialog>
{/if}

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
