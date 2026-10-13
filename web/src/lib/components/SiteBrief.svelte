<script lang="ts">
	import { MODELS_PATH } from '$lib/models';
	import { SITE_NAME } from '$lib/site';
</script>

<section class="band brief" id="how-to-predict">
	<div class="page inside">
		<div class="head">
			<h2 class="page-title type-h1">NBA predictions, in four steps</h2>

			<p class="statement measure">
				{SITE_NAME}
				is free to use and does not require an account. Predictions 
				are made on upcoming NBA games for a variety of useful statistics. Evaluation and accuracy metrics 
				for every model on an unseen test set are publicly displayed on each model category's page.
			</p>
		</div>

		<ol class="flight">
			<li class="tread">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Choose a model category</h3>
				<p class="muted">
					Select one of the three model categories
					<a href={MODELS_PATH}> above </a>
					to predict on the stats of the category type. Each category lists
					the supported statistics for prediction within it.
				</p>
			</li>
			<li class="tread">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Pick the game</h3>
				<p class="muted">
					Every upcoming game is displayed in the 
					<i>Upcoming Games</i> 
					section of each model category's prediction page. Choose one of the game cards to select it as
					the target game. 
				</p>
			</li>
			<li class="tread">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Specify what to predict</h3>
				<p class="muted">
					Name the desired predicted statistic, and the target player or team the category asks for. Then, other
					parameters, such as the injured or new players in the game, can be changed to affect the prediction
					outcomes.
				</p>
			</li>
			<li class="tread block-plane">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Predict!</h3>
				<p class="muted">
					Press the 
					<i>Predict</i>
					button, and wait a few seconds for the model to make the prediction. 
					The answer is drawn as a chart, and the line across it is yours to move freely.
				</p>
			</li>
		</ol>
	</div>
</section>

<style>
	.brief {
		padding-block: calc(var(--space-8) + var(--space-6)) var(--space-7);
	}

	.inside {
		display: flex;
		container-type: inline-size;
		flex-direction: column;
		gap: var(--space-6);
	}

	.head {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.head h2 {
		text-wrap: balance;
	}

	.statement {
		font-size: var(--type-note);
	}

	.flight {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
		counter-reset: step;
		/* Indent of each step from the one above it. */
		--tread: clamp(0.75rem, 3.2cqi, 3.5rem);
	}

	.tread {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-content: center;
		align-items: baseline;
		gap: var(--space-3) var(--space-4);
		padding: var(--space-5);
		counter-increment: step;
	}

	.tread p {
		grid-column: 1 / -1;
	}

	.tread:nth-child(2) {
		margin-inline-start: var(--tread);
	}

	.tread:nth-child(3) {
		margin-inline-start: calc(var(--tread) * 2);
	}

	.tread:nth-child(4) {
		margin-inline-start: calc(var(--tread) * 3);
	}

	.tread:nth-child(1) {
		background: var(--surface);
	}

	.tread:nth-child(2) {
		background: var(--panel);
	}

	.tread:nth-child(3) {
		background: var(--surface-sunken);
	}

	.number::before {
		content: counter(step, decimal-leading-zero);
	}

	@media (min-width: 64rem) {
		.flight {
			grid-auto-rows: 1fr;
		}

		.head {
			display: grid;
			grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
			align-items: end;
			gap: var(--space-6);
		}

		.tread {
			grid-template-columns: auto minmax(0, 0.8fr) minmax(0, 1.2fr);
			gap: var(--space-5);
			padding: var(--space-6);
		}

		.tread p {
			grid-column: auto;
		}
	}
</style>
