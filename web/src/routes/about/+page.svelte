<!--
	What the site is, and nothing about any one model.

	No model is explained here and no accuracy figure appears here. A reader who wants either should
	go to the family's own page, so this page does not grow a section every time a family is added.

	Reading a prediction is the annotated answer block rather than a passage, because the block is
	what a reader has to learn and it teaches itself once it is labelled.
-->
<script lang="ts">
	import AnnotatedAnswer from '$lib/components/AnnotatedAnswer.svelte';
	import { pageTitle, SITE_NAME } from '$lib/site';
	import { MODELS_PATH } from '$lib/models';
</script>

<svelte:head>
	<title>{pageTitle('About')}</title>
	<meta
		name="description"
		content="What this site is, how to read a prediction, how it works, and its limitations"
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
			Each model outputs a probability distribution over the range of possible outcomes for a targeted statistic,
			allowing for precise post-prediction calculations of the
			<b class="under">under</b>,
			<b class="push">push</b>,
			and
			<b class="over">over</b>
			values for a
			specified line.
		</p>
		<p>
			Head to the
			<a href={MODELS_PATH}>Models</a>
			section to select from the available model types.
			Visit a specific model type's
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
		<h3>What is machine learning?</h3>
		<p>
			...
		</p>
		<h3>How are models trained?</h3>
		<p>
			Historical NBA game logs containing player and team box scores are collected from
			<a href="https://www.balldontlie.io/" target="_blank" rel="noreferrer">BALLDONTLIE</a>,
			spanning 35,000 NBA games played since 1996.
		</p>
		<p>
			To train a model, the raw game logs are first processed, removing redundant data points and feature
			engineering new ones.
			Then, the dataset is split by date into training, validation, and test splits.
			The training set is used to adjust the model weights. After the training epochs have elapsed, the
			weights that produces the least error when inferencing on the validation dataset is kept.
			Evaluation metrics are then calculated based on a final pass of the trained model on the test split.
		</p>
		<p>
			Each model has a unique data processing step and tailored hyperparameters, each chosen to maximize the
			accuracy of predictions. More information on the engineered features and evaluation scores of a model
			is outlined within their category's
			<em>About</em>
			page.
		</p>
	</section>

	<section id="limitations">
		<h2>Limitations</h2>
		<p>
			<em>MACHINE LEARNING IS NOT MAGIC.</em>
		</p>
		<p>
			While it is a powerful tool, at its core, the models on this site are nothing more than a
			series of matrix multiplications, activation functions, normalizations, and other mathematical
			operations. 
		</p>
		<p>
			The predicted values are not guaranteed nor always correct. Do not interpret them as such. 
		</p>
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
