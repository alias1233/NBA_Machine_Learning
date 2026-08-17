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
	import { pageTitle, SITE_NAME } from '$lib/site';
	import { MODELS_PATH } from '$lib/models';

	/** Placeholders. The wording is the user's to settle, so each one reads as unwritten. */
	const QUESTIONS = [
		{ question: 'First question, not written yet', answer: 'This answer is not written yet.' },
		{ question: 'Second question, not written yet', answer: 'This answer is not written yet.' },
		{ question: 'Third question, not written yet', answer: 'This answer is not written yet.' },
		{ question: 'Fourth question, not written yet', answer: 'This answer is not written yet.' }
	];
</script>

<svelte:head>
	<title>{pageTitle('About')}</title>
	<meta
		name="description"
		content="What this site is, how to read a prediction, how it works, and disclaimers."
	/>
</svelte:head>

<div class="page sections">
	<h1 class="page-title">About</h1>

	<section id="what">
		<h2>What this is</h2>
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
			section to select from the available model types. Visit a specific model type's
			<em>About</em>
			page to learn more about what each model predicts.
		</p>
	</section>

	<section id="reading">
		<h2>Reading a prediction</h2>

		<AnnotatedAnswer />
	</section>

	<section id="how">
		<h2>How it works</h2>

		<h3><em>What is machine learning?</em></h3>
		<p>
			...
		</p>
		<p>
			...
		</p>

		<h3><em>How are models trained?</em></h3>
		<p>
			Historical NBA game logs containing player and team box scores are first collected from 
			our data provider,
			<a href="https://www.balldontlie.io/" target="_blank" rel="noreferrer">BALLDONTLIE</a>.
			The raw game logs are then processed by removing redundant data points and engineering
			new features.
		</p>
		<p>
			The dataset is partitioned by date into training, validation, and test splits.
			During the learning phase, the model makes predictions on the training dataset, and 
			its internal weights are adjusted based on the result. After the training epochs have 
			elapsed, the weights that produced the least error when inferencing on the validation 
			dataset are kept. Evaluation metrics are then calculated based on a final pass of the 
			trained model on the test split.
		</p>
		<p>
			Each model has a unique data processing step and tailored hyperparameters, each chosen 
			to maximize the accuracy of predictions. More information detailing the engineered features 
			and evaluation scores of a model is outlined within their category's
			<em>About</em>
			page.
		</p>
	</section>

	<section id="disclaimers">
		<h2>Disclaimers</h2>

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

	<section id="questions">
		<h2>Common questions</h2>

		<Faq questions={QUESTIONS} name="about" />
	</section>
</div>

<style>
	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
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
