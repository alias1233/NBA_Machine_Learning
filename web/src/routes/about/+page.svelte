<!--
	What the site is, and nothing about any one model.

	No model is explained here and no accuracy figure appears here. A reader who wants either should
	go to the family's own page, so this page does not grow a section every time a family is added.

	Reading a prediction is the annotated answer block rather than a passage, because the block is
	what a reader has to learn and it teaches itself once it is labelled.
-->
<script lang="ts">
	import AnnotatedAnswer from '$lib/components/AnnotatedAnswer.svelte';
	import Faq from '$lib/components/Faq.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import SectionIndex from '$lib/components/SectionIndex.svelte';
	import { pageTitle, SITE_DESCRIPTION, SITE_NAME } from '$lib/site';
	import { MODELS_PATH } from '$lib/models';

	/**
	 * Placeholders, apart from the first question. The wording is the user's to settle, so each one
	 * reads as unwritten.
	 *
	 * Which games can be predicted is asked here rather than on a family page, because the answer is
	 * the same for every family and would otherwise be restated once per family.
	 */
	const QUESTIONS = [
		{ 
			question: `Why can't I find a scheduled game in the Upcoming Games section of a prediction page?`, 
			answer: [
				`The site currently does not support predicting on preseason games, and they do not appear
				in the Upcoming Games section.`,
				`If your target game is a regular season or playoff game, then simply wait for the teams 
				in your target game to finish playing the games that they have scheduled before your target 
				game, and the Upcoming Games section should automatically update soon after.`,
				`The only games that are shown in the Upcoming Games section are games between teams that both do not 
				have an earlier scheduled game. This ensures all predictions are made with updated information.`
			]
		},
		{ 
			question: `Why do some probability distribution graphs contain bars that range over multiple individual values?`, 
			answer: [
				`The models assign a probability to every outcome within the predicted statistic's common 
				range of occurance. However, for statistics which span a wide range, it is challenging for
				the model to provide accurate probabilities for every single value within the interval,
				especially if there are fewer data samples to train on.`,
				`In these cases, the possible outcomes of the statistic are "bucketed", grouping intervals
				of outcomes together. This lowers the total number of possible outcomes, reducing the
				complexity of the task that the model has to do, and increasing accuracy.`
			]
		},
		{ 
			question: 'Can I make predictions on mock trades just for fun?', 
			answer: [
				`Yes! Predicting supports any custom changes to a team's roster. Simply begin typing in the 
				player selector's input field to search for players league-wide, even if they do not 
				belong to the current team. You can also remove players from a team arbitrarily as well.`
			]
		},
	];

	// The anchors are fixed. Every answer block on the site links to #reading, so that one in
	// particular can never be renamed.
	const SECTIONS = [
		['what', 'What this is'],
		['reading', 'Reading a prediction'],
		['how', 'How it works'],
		['questions', 'FAQ'],
		['disclaimers', 'Disclaimers']
	];
</script>

<svelte:head>
	<title>{pageTitle('About')}</title>
	<meta
		name="description"
		content="What this site is, how to read a prediction, how it works, and disclaimers."
	/>
</svelte:head>

<PlateBand title="About" lede={SITE_DESCRIPTION} />

<div class="page reading indexed">
	<SectionIndex sections={SECTIONS} label="Sections of this page" />

	<div class="sections">
		<section id="what">
			<h2 class="section-rule">What this is</h2>
			<p>
				<a href="/">{SITE_NAME}</a>
				is a collection of machine learning models that predict statistics of future NBA games.
			</p>
			<p>
				Each model outputs a probability distribution over the range of possible outcomes for 
				a targeted statistic, allowing for precise calculations of the predicted
				<b class="under">under</b>,
				<b class="push">push</b>,
				and
				<b class="over">over</b>
				values for a specified line.
			</p>
			<p>
				Head to the
				<a href={MODELS_PATH}>Models</a>
				section to select from the available model categories. Visit a model category's
				<em>Info</em>
				page to learn more about what specific models within the category predict.
			</p>
		</section>

		<section id="reading">
			<h2 class="section-rule">Reading a prediction</h2>

			<AnnotatedAnswer />
		</section>

		<section id="how">
			<h2 class="section-rule">How it works</h2>

			<h3><em>Model Architecture</em></h3>
			<p>
				The models on this site utilize a multimodal architecture consisting of a Gated Recurrent Unit
				(GRU) and a Multi-Layer Perceptron (MLP).
			</p>
			<p>
				The GRU is fed sequential game data, encoding in its hidden states a representation of
				the modeled process. This encoded representation is then fed into the MLP, along with relevant
				static data points, to produce the final output logits.
			</p>

			<h3><em>Training the Models</em></h3>
			<p>
				Historical NBA game logs containing player and team box scores are first collected from 
				our data provider,
				<a href="https://www.balldontlie.io/" target="_blank" rel="noreferrer">BALLDONTLIE</a>.
				Before training, the raw game logs are processed, removing redundant data points and 
				engineering new features.
			</p>
			<p>
				The dataset is partitioned by date into training, validation, and test splits.
				During the learning phase, the model makes predictions on the training dataset, and 
				its weights are adjusted based on comparing the predicted values to the actual values,
				allowing the model to "learn". After the training epochs have elapsed, the weights that 
				produced the least error when inferencing on the validation dataset are kept. 
			</p>
			<p>
				Each model has a unique data processing step and tailored hyperparameters, each chosen 
				to improve the accuracy of predictions.
			</p>

			<h3><em>Evaluating the Models</em></h3>
			<p>
				Evaluation metrics are calculated based on a final pass of the trained model on the unseen
				test split. A simple baseline model, which naively answers with the season's usual spread 
				of outcomes, is also evaluated on the test split as a comparison tool.
			</p>
			<p>
				These evaluation scores are public, with each model's scores outlined within their category's
				<em>Info</em>
				page. The baseline model's scores are shown too.
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
