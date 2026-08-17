<!--
	The models a family holds, one card each, in a plain grid.

	Every model is on the page at once and nothing is hidden behind a control, which is what a reader
	deciding whether to trust a family needs. Choosing a card opens what that model measured on games
	it never saw while it was being fitted.

	The figures are not on the page. Opening a card is what asks for that one model's, so a reader
	who opens none costs the service nothing, and what has been fetched is kept for the rest of the
	visit rather than asked for again.

	The visuals here are deliberately plain and are meant to be redrawn.
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
	 * A name is in here once its fetch has finished, and its value is null where the model has never
	 * been scored or where the fetch failed. Both read the same way to a reader: no figures.
	 */
	const scores = new SvelteMap<string, ModelEvaluation | null>();
	let loading = $state<string | null>(null);

	const scored = $derived(opened ? (scores.get(opened.name) ?? null) : null);
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

		scores.set(model.name, response?.ok ? await response.json() : null);
		loading = null;
	}

	/** A figure written the way its unit asks to be read. */
	function figure(value: number, unit: Metric['unit']): string {
		if (unit === 'probability') return `${(value * 100).toFixed(1)}%`;

		return value.toFixed(3);
	}

	const day = (date: string) => new Date(`${date}T00:00:00`).toLocaleDateString();
</script>

<ul class="models">
	{#each models as model (model.name)}
		<li>
			<button type="button" class="block model" onclick={() => open(model)}>
				<h3>{model.title}</h3>
				<p class="small muted">{model.description}</p>

				{#if !model.published}
					<span class="tag micro">Not published yet</span>
				{/if}
			</button>
		</li>
	{/each}
</ul>

{#if opened}
	<dialog bind:this={dialog} onclose={() => (opened = null)}>
		<header>
			<h3>{opened.title}</h3>
			<button type="button" class="button" onclick={() => dialog?.close()}>Close</button>
		</header>

		{#if fetching}
			<p class="small muted">Reading what this model measured…</p>
		{:else if !scored}
			<p class="small muted">This model has not been scored yet.</p>
		{:else}
			<p class="small muted">
				{scored.samples.toLocaleString()} held-out games, {day(scored.first_game)} to {day(
					scored.last_game
				)}.
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
							<td>{metric.floor === null ? '—' : figure(metric.floor, metric.unit)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</dialog>
{/if}

<style>
	.models {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--model-card)), 1fr));
		gap: var(--space-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.model {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
		width: 100%;
		height: 100%;
		padding: var(--space-4);
		font: inherit;
		text-align: start;
		cursor: pointer;
	}

	dialog {
		max-width: min(100%, var(--control-column));
		padding: var(--space-5);
		background: var(--surface);
		color: var(--ink);
		border: var(--rule-block);
		border-radius: var(--radius);
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
</style>
