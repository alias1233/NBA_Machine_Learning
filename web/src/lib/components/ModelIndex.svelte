<!--
	The models a family holds, printed as an index.

	Every model is on the page at once and nothing is fetched, because the figures are the only
	content on this site that nobody else has and a figure fetched after the page has been sent
	reaches neither a search engine nor a reader with no scripting. The service sends each model's
	scored file with its card, the page is rendered around them, and folding a row open shows what
	that model measured on games it never saw while it was fitted.

	A row is a `<details>`, so the whole index is one column: a run of rows that grow in place reads
	as an index being opened, where two runs side by side would leave a hole beside whichever row was
	opened. The row's own heading carries the model's headline figure, so a reader comparing a family
	can scan the column without opening anything.

	Every figure is read against the baseline beside it, and the panel says which of the two won it: a
	drawn check against the better of the pair, in the same green a chart reads an over in, and the word
	in the row's own heading for anybody who cannot see the mark. Which direction counts as better is
	the model's own to say, because on some of these figures a smaller number is the good one. A measure
	the baseline could not be scored on has no winner, and neither does a tie.
-->
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
		<!-- The model's own first figure, which is the one it leads with wherever it is read. -->
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
						<!-- Held out is spelled out rather than named, because it is the whole reason the
						     figures below mean anything and the reader is meeting the idea for the first time. -->
						<p class="small muted">
							Scored on {scored.samples.toLocaleString()} held-out games the model never saw during
							training, from {day(scored.first_game)} to {day(scored.last_game)}. Baseline is what
							answering with the season's usual spread of outcomes scores on those same games.
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
				</div>
			</details>
		</li>
	{/each}
</ul>

<!-- Drawn rather than typed, in the one stroke weight every mark on this site is drawn in. -->
{#snippet check()}
	<svg class="check" viewBox="0 0 24 24" aria-hidden="true">
		<path d="M4.5 13 10 18.5 19.5 6" />
	</svg>
{/snippet}

<style>
	/* An index, not a grid: one column of rows, with a rule between. */
	.index {
		margin: 0;
		padding: 0;
		list-style: none;
		border-top: var(--rule-panel);
	}

	.index > li {
		border-bottom: var(--rule-panel);
	}

	/* The name and what it answers, then the model's headline figure, then the mark saying which way
	   the row is going. The whole heading is the control, so it holds the row's own padding. */
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

	/* The figure the model leads with, so a family can be read down without opening a row. */
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

	/* Set in from the heading above it, and capped, because a table of three columns read across a
	   76rem page is a line nobody can track back. */
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

	/* The headline figure is the first thing to go where a row has no room for all three. */
	@media (width < 30rem) {
		.headline .micro {
			display: none;
		}
	}
</style>
