<script lang="ts">
	import AnnotatedAnswer from '$lib/components/AnnotatedAnswer.svelte';
	import EditorialMeta from '$lib/components/EditorialMeta.svelte';
	import Faq from '$lib/components/Faq.svelte';
	import PageMetadata from '$lib/components/PageMetadata.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import SectionIndex from '$lib/components/SectionIndex.svelte';
	import { pageTitle, PUBLIC_SITE_DESCRIPTION, SITE_NAME } from '$lib/site';
	import { MODELS_PATH } from '$lib/models';
	import { articleSchema, faqSchema } from '$lib/seo';

	const DESCRIPTION = 'How Bazaar Ball makes NBA predictions, measures model quality, and explains uncertainty.';

	let { data } = $props();

	const QUESTIONS = [
		{
			question: 'Why is an upcoming NBA game missing from the Upcoming Games section?',
			answer: [
				`The site currently does not support predicting on preseason games, and they do not appear
				in the Upcoming Games section.`,
				`If your target game is a regular season or playoff game, then simply wait for the teams 
				in your target game to finish playing the games that they have scheduled before your target 
				game, and the Upcoming Games section should automatically update soon after.`,
				'This ensures each prediction is based on the latest available information.'
			]
		},
		{
			question: `Why do some models' chart bars cover multiple values?`,
			answer: [
				`For a statistic with a wide range of possible outcomes, a bar can represent a small interval 
				of nearby outcomes rather than one exact value. Grouping those values into one bucket reduces 
				the complexity of the prediction task for the model, increasing its accuracy.`
			]
		},
		{
			question: 'Can I make predictions on mock, what-if rosters?',
			answer: [
				`Yes! You can remove any players from their teams, and add any player currently in the league 
				to any team's roster. Simply begin typing in the player selector's input field to search for 
				players league-wide.`,
				`Predictions still function normally, with the model's predicted outcomes
				adjusting based on the custom changes made.`
			]
		},
	];

	// Every prediction result links to #reading, so do not rename that anchor.
	const SECTIONS = [
		['what', 'What it predicts'],
		['reading', 'Reading a prediction'],
		['how', 'How it works'],
		['evaluation-metrics', 'Evaluation metrics'],
		['questions', 'FAQ'],
		['disclaimers', 'Disclaimers']
	];
</script>

<PageMetadata
	title="About"
	description={DESCRIPTION}
	path="/about"
	article
	schema={[
		articleSchema({ name: pageTitle('About'), description: DESCRIPTION, path: '/about' }),
		faqSchema(QUESTIONS)
	]}
/>

<PlateBand title="About" lede={PUBLIC_SITE_DESCRIPTION} />

<div class="page reading indexed">
	<SectionIndex sections={SECTIONS} label="Sections of this page" />

	<div class="sections">
		<section id="what">
			<h2 class="section-rule">What is Bazaar Ball?</h2>
			<p>
				<a href="/">{SITE_NAME}</a>
				is a collection of machine learning models that predicts player, team, and game statistics 
				for upcoming NBA games. Each model outputs a range of possible outcomes and the probabilities assigned to 
				each value, rather than one certain answer.
			</p>
			<p>
				The resulting distribution can be used to calculate the predicted
				<b class="under">under</b>,
				<b class="push">push</b>,
				and
				<b class="over">over</b>
				values for every possible line.
			</p>
			<p>
				Head to the
				<a href={MODELS_PATH}>Models</a>
				section to choose from the available model categories. Each category’s page lists the models
				within it and displays their evaluation metrics under the prediction results.
			</p>
		</section>

		<section id="reading">
			<h2 class="section-rule">How do I read a prediction?</h2>

			<AnnotatedAnswer />
		</section>

		<section id="how">
			<h2 class="section-rule">How does Bazaar Ball make a prediction?</h2>

			<p>
				The models compare recent game results, team context, schedule context, and who is expected to
				play. A sequence model reads the run of past games, then combines it with the facts about the
				upcoming game to estimate the likelihood of each outcome.
			</p>
			<p>
				Historical schedules, player game statistics, and player availability data are collected from
				the BALLDONTLIE NBA API.
			</p>
			<p class="source small">
				Source: <a href="https://docs.balldontlie.io/" target="_blank" rel="noreferrer">BALLDONTLIE NBA API documentation</a>.
			</p>
		</section>

		<section id="evaluation-metrics">
			<h2 class="section-rule">What do the evaluation metrics mean?</h2>
			<p>
				These are the evaluation metrics used by the current models. Each model’s page shows the 
				value that a model scored and its baseline comparison.
			</p>
			<p>
				Evaluation metrics are calculated based on a final pass of the trained model on a test split
				that was unseen by the model during training. A simple baseline algorithm, which naively answers 
				with the season's usual spread of outcomes, is also evaluated on the test split as a comparison tool.
			</p>
			<p class="source small">
				Source: <a href="/#models">each model family’s published evaluation metrics</a>.
			</p>

			{#if data.metrics.length > 0}
				<dl class="metric-definitions">
					{#each data.metrics as metric (metric.key)}
						<div>
							<dt><h3>{metric.label}</h3></dt>
							<dd>{metric.description}</dd>
						</div>
					{/each}
				</dl>
			{:else}
				<p class="small muted">The evaluation metric definitions are unavailable right now.</p>
			{/if}
		</section>

		<section id="questions">
			<h2 class="section-rule">Frequently Asked Questions</h2>

			<Faq questions={QUESTIONS} name="about" />
		</section>

		<section id="disclaimers">
			<h2 class="section-rule">Disclaimers</h2>

			<h3><em>Prediction limitations</em></h3>
			<p>
				This site is for informational and entertainment purposes only. Predictions are 
				<em>not</em> 
				betting advice.
			</p>
			<p>
				At their core, the models on this site are nothing more than a structured series of matrix 
				multiplications, activation functions, normalizations, and other mathematical operations.
				The predicted outcomes are not guaranteed nor always correct. Do not interpret them as such. 
			</p>

			<h3><em>Affiliation</em></h3>
			<p>
				This site is not affiliated with, endorsed by, or sponsored by the National Basketball Association.
			</p>
		</section>

		<EditorialMeta path="/about" />
	</div>
</div>

<style>
	.reading {
		padding-block-start: var(--space-7);
	}

	.sections {
		gap: var(--space-7);
		min-width: 0;
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	section h2 {
		margin-block-end: var(--space-1);
	}

	.over {
		color: var(--over);
	}

	.under {
		color: var(--under);
	}

	.push {
		color: var(--push);
	}

	.metric-definitions {
		margin: var(--space-2) 0 0;
	}

	.metric-definitions > div {
		padding-block: var(--space-4);
		border-top: var(--rule-panel);
	}

	.metric-definitions > div:last-child {
		border-bottom: var(--rule-panel);
	}

	.metric-definitions dt,
	.metric-definitions dd {
		margin: 0;
	}

	.metric-definitions dd {
		max-width: var(--measure);
		margin-block-start: var(--space-2);
	}

</style>
