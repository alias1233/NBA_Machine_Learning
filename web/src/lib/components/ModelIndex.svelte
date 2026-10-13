<script lang="ts">
	import { figure, winner } from '$lib/model-evaluation';
	import type { ScoredModel } from '$lib/types';

	type Props = {
		models: ScoredModel[];
	};

	let { models }: Props = $props();

	const day = (date: string) => new Date(`${date}T00:00:00`).toLocaleDateString();
</script>

<ul class="index">
	{#each models as model (model.name)}
		{@const scored = model.evaluation}
		{@const headline = scored?.metrics[0] ?? null}

		<li>
			<details class="entry">
				<summary>
					<span class="says">
						<span class="name type-h3">{model.title}</span>
						<span class="what small muted">{model.description}</span>
					</span>

					<span class="state">
						{#if !model.published}
							<span class="tag micro">Not published yet</span>
						{:else if headline}
							<span class="headline">
								<span class="micro muted">{headline.label}</span>
								<span class="numeric">{figure(headline.value, headline.unit)}</span>
							</span>
						{/if}
					</span>

					<svg class="mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
						<path d="M5 9 L12 16 L19 9" />
					</svg>
				</summary>

				<div class="measured">
					{#if !scored}
						<p class="small muted">This model has not been scored yet.</p>
					{:else}
						<p class="small muted">
							Scored on {scored.samples.toLocaleString()} games from {day(scored.first_game)} to {day(scored.last_game)}.
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
										{#if better}
											<span class="visually-hidden">
												{better === 'model' ? 'The model is better here.' : 'The baseline is better here.'}
											</span>
										{/if}
									</th>
										<td>
											<span class="read" class:won={better === 'model'}>
												{figure(metric.value, metric.unit)}
												{#if better === 'model'}{@render check()}{/if}
											</span>
										</td>
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
				</div>
			</details>
		</li>
	{/each}
</ul>

{#snippet check()}
	<svg class="check" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M4.5 13 10 18.5 19.5 6" />
	</svg>
{/snippet}

<style>
	.index {
		margin: 0;
		padding: 0;
		list-style: none;
		border-top: var(--rule-panel);
	}

	.index > li {
		border-bottom: var(--rule-panel);
	}

	.entry > summary {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		min-height: var(--tap-target);
		padding: var(--space-3) var(--space-2);
		cursor: pointer;
		transition: background var(--motion-fast) var(--ease-in);
	}

	.entry > summary:hover,
	.entry > summary:focus-visible {
		background: var(--panel);
	}

	.entry > summary:hover .name {
		color: var(--accent);
	}

	.says {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		flex: 1;
		min-width: 0;
	}

	.state {
		flex: none;
	}

	.headline {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		align-items: flex-end;
		text-align: end;
	}

	.mark {
		flex: none;
		width: var(--icon);
		height: var(--icon);
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
		transition: rotate var(--motion) var(--ease-in);
	}

	.entry[open] > summary .mark {
		rotate: 180deg;
	}

	.measured {
		display: flex;
		flex-direction: column;
		max-width: var(--measure);
		padding: 0 var(--space-2) var(--space-5);
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

	.read {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		white-space: nowrap;
	}

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

	@media (width < 30rem) {
		.headline .micro {
			display: none;
		}
	}
</style>
