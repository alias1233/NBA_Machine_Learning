<script lang="ts">
	import { tick } from 'svelte';

	import AdSlot from '$lib/components/AdSlot.svelte';
	import ModelIndex from '$lib/components/ModelIndex.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PageMetadata from '$lib/components/PageMetadata.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { FAMILY_MODELS_SECTION } from '$lib/models';
	import { flowingHeight, MOTION, MOTION_IMPACT, MOTION_SLOW, settled } from '$lib/motion';
	import { phone } from '$lib/screen';
	import { stopWalking, walkTo } from '$lib/scroll';
	import { webPageSchema } from '$lib/seo';

	import type { ScoredModel } from '$lib/types';
	import type { Snippet } from 'svelte';

	type Props = {
		title: string;
		/** Path of this family's page. */
		path: string;
		/** One sentence, for a search result and a shared link. */
		privateDescription: string;
		/** One sentence, shown as the page lede.*/
		publicDescription: string;
		/** Short instruction shown above the form. */
		standing: string;
		/** Every model in the family, with its evaluation results. */
		scored: ScoredModel[];
		/** False when the service has no models this page can show. */
		hasModels: boolean;
		/** False when the service could not be reached. Different from having no models. */
		answering: boolean;
		/** The prediction response. A new object means a new completed prediction. */
		prediction: unknown | null;
		/** Model used for the completed prediction. */
		model: string;
		/** True when the URL already has a request that returned a result or an error. */
		hasAnswer: boolean;
		/** List of upcoming games, shown first. Left out if the family does not predict on a game. */
		board?: Snippet;
		/** Heading that shows the selected game. Left out when there is no game list. */
		matchup?: Snippet;
		controls: Snippet;
		/** Must render a single element. It is used for the result, the loading skeleton and the error. */
		result: Snippet<[opening: boolean]>;
	};

	let {
		title,
		path,
		privateDescription,
		publicDescription,
		standing,
		scored,
		hasModels,
		answering,
		prediction,
		model,
		hasAnswer,
		board,
		matchup,
		controls,
		result
	}: Props = $props();

	let answerColumn = $state<HTMLElement>();
	let controlsColumn = $state<HTMLElement>();
	let trackedPrediction = $state.raw<unknown>(null);

	/** True once the result block has expanded to full size, which happens on the first submit. */
	// svelte-ignore state_referenced_locally
	let opened = $state(hasAnswer);
	let opening = $state(false);

	$effect(() => {
		if (prediction === null || prediction === trackedPrediction) return;

		window.dataLayer?.push({
			event: 'prediction_made',
			prediction_family: path.slice('/models/'.length),
			prediction_model: model
		});
		trackedPrediction = prediction;
	});

	/** Scrolls to the result area. On the first call it also expands the result block. */
	export async function reveal(asking?: Promise<unknown>): Promise<void> {
		stopWalking();

		if (!opened) {
			const walking = walkTo(answerColumn, {
				block: 'start',
				flowing: MOTION_IMPACT,
				always: true
			});

			await Promise.race([walking, settled(MOTION)]);

			opening = true;
			opened = true;
			await tick();
			await Promise.all([walking, settled(MOTION_IMPACT)]);
			opening = false;
			return;
		}

		walkTo(answerColumn, { block: 'start', flowing: phone.current ? MOTION_SLOW : asking });

		if (phone.current && asking) asking.then(stopWalking, stopWalking);
	}

	/** Scrolls the form to the top of the screen, under the header. */
	export function revealControls(): void {
		walkTo(controlsColumn, { block: 'start', always: true });
	}
</script>

<!-- Uses the path without a query string, so every parameter combination shares one canonical URL. -->
<PageMetadata
	{title}
	description={privateDescription}
	{path}
	schema={webPageSchema({ name: title, description: privateDescription, path })}
/>

<PlateBand {title} lede={publicDescription}>
	{#snippet action()}
		{#if scored.length > 0}
			<a class="small text-link" href={`#${FAMILY_MODELS_SECTION}`}>
				See every model and how it scores
			</a>
		{/if}
	{/snippet}
</PlateBand>

<div class="page work">
	<div class="lead">
		<section class="standing">
			<p>{standing}</p>
		</section>

		{#if !hasModels}
			{#if answering}
				<Notice>No model here can answer yet.</Notice>
			{:else}
				<Notice>
					The prediction service is not answering, so nothing can be predicted right now. Try again in a
					few minutes.
				</Notice>
			{/if}
		{:else}
			<div class="request">
				<div class="columns" class:boardless={!board}>
					{#if board}
						<div class="board-column">{@render board()}</div>
					{/if}

					<section class="controls" aria-labelledby="controls-column" bind:this={controlsColumn}>
						<h2 class="column-label micro" id="controls-column">What to predict</h2>
						{@render matchup?.()}
						<div class="panel">
							{@render controls()}
						</div>
					</section>
				</div>

				<section class="answer" aria-labelledby="answer-column" bind:this={answerColumn}>
					<h2 class="column-label micro" id="answer-column">Answer</h2>

					<div class="answer-result" class:opening use:flowingHeight>
						<div class="swap">
							{#if opened}
								<div>{@render result(opening)}</div>
							{:else}
								<p class="prompt type-h2">Make a prediction first.</p>
							{/if}
						</div>
					</div>
				</section>
			</div>
		{/if}
	</div>

	{#if scored.length > 0}
		<section
			class="listing"
			class:unanswered={!opened}
			id={FAMILY_MODELS_SECTION}
			aria-labelledby="models-section"
		>
			<div class="head">
				<h2 class="page-title type-h1" id="models-section">All models</h2>

				<p class="said">
					Click on a model tab to reveal the evaluation scores of the model.
				</p>
			</div>

			<ModelIndex models={scored} />

			<p>
				<a class="small text-link" href="/about#evaluation-metrics">
					Learn what each evaluation metric means
				</a>
			</p>
		</section>
	{/if}

	<AdSlot place="modelBelowResult" />
</div>

<style>
	.work {
		display: flex;
		flex-direction: column;
		gap: var(--space-7);
		padding-block-start: var(--space-5);
	}

	.lead {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.standing p {
		color: var(--ink-muted);
		font-size: var(--type-body);
		text-wrap: pretty;
	}

	.columns {
		display: grid;
		gap: var(--space-6);
	}

	.request {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.board-column,
	.controls,
	.answer {
		min-width: 0;
	}

	.controls {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		container-type: inline-size;
		container-name: controls;
	}

	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		container-type: inline-size;
		container-name: answer-column;
	}

	.answer-result {
		min-width: 0;
	}

	.swap {
		display: grid;
	}

	.swap > * {
		grid-area: 1 / 1;
		min-width: 0;
	}

	.prompt {
		padding-block-end: var(--space-3);
		color: var(--ink-muted);
	}

	.answer-result.opening {
		position: relative;
		isolation: isolate;
		overflow: clip;
		animation: open-answer var(--motion-impact) var(--ease-in);
	}

	.answer-result.opening::after {
		content: '';
		position: absolute;
		z-index: 1;
		inset: 0;
		background: linear-gradient(
			to right,
			transparent calc(100% - 2px),
			var(--accent-block) calc(100% - 2px)
		);
		opacity: 0;
		pointer-events: none;
		animation: open-edge var(--motion-impact) var(--ease-in);
	}

	@keyframes open-answer {
		from {
			clip-path: inset(0 100% 0 0);
		}

		to {
			clip-path: inset(0);
		}
	}

	@keyframes open-edge {
		from {
			opacity: 0;
			transform: translateX(-100%);
		}

		8%,
		82% {
			opacity: 1;
		}

		to {
			opacity: 0;
			transform: translateX(0);
		}
	}

	.listing {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		margin-block-start: var(--space-6);
	}

	.listing.unanswered {
		margin-block-start: var(--space-8);
	}

	.head {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.head h2 {
		text-wrap: balance;
	}

	.said {
		color: var(--ink-muted);
		font-size: var(--type-note);
		text-wrap: pretty;
	}

	@media (width < 40rem) {
		/* The result replaces a placeholder, so it must not become the browser's scroll anchor. */
		.answer {
			overflow-anchor: none;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.answer-result.opening {
			animation: none;
		}

		.answer-result.opening::after {
			display: none;
		}
	}

	@media (min-width: 64rem) {
		.columns {
			grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
			align-items: start;
			column-gap: var(--space-6);
		}

		.columns.boardless {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
