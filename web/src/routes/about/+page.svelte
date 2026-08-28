<!--
	What the site is, and nothing about any one model.

	No model is explained here and no accuracy figure appears here. A reader who wants either should
	go to the family's own page, so this page does not grow a section every time a family is added.

	Reading a prediction is the annotated answer block rather than a passage, because the block is
	what a reader has to learn and it teaches itself once it is labeled.
-->
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

	/** Site-wide questions belong here so every prediction page can point to one answer. */
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

	// The anchors are fixed. Every answer block on the site links to #reading, so that one in
	// particular can never be renamed.
	const SECTIONS = [
		['what', 'What it predicts'],
		['reading', 'Reading a prediction'],
		['how', 'How it works'],
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
				section to choose from the available model categories. Each category’s <em>Info</em> page explains 
				the models within the category and displays their evaluation metrics.
			</p>
		</section>

		<section id="reading">
			<h2 class="section-rule">How do I read a prediction?</h2>

			<AnnotatedAnswer />
		</section>

		<section id="how">
			<h2 class="section-rule">How does Bazaar Ball make a prediction?</h2>

			<h3><em>What does the model use?</em></h3>
			<p>
				The models compare recent game results, team context, schedule context, and who is expected to
				play. A sequence model reads the run of past games, then combines it with the facts about the
				upcoming game to estimate the likelihood of each outcome.
			</p>

			<h3><em>Where does the data come from?</em></h3>
			<p>
				Historical schedules, player game statistics, and player availability data are collected from
				the BALLDONTLIE NBA API.
			</p>
			<p class="source small">
				Source: <a href="https://docs.balldontlie.io/" target="_blank" rel="noreferrer">BALLDONTLIE NBA API documentation</a>.
			</p>

			<h3><em>How are the models tested?</em></h3>
			<p>
				Evaluation metrics are calculated based on a final pass of the trained model on a test split
				that was unseen by the model during training. A simple baseline algorithm, which naively answers 
				with the season's usual spread of outcomes, is also evaluated on the test split as a comparison tool.
			</p>
			<p>
				A model category's 
				<em>Info</em>
				page outlines the evaluation metrics of the models within the category, along with the values that the 
				baseline scored.
			</p>
			<p class="source small">
				Source: <a href="/#models">each model family’s published evaluation metrics</a>.
			</p>
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

</style>
