<!--
	What the site is, and nothing about any one model.

	No model is explained here and no accuracy figure appears here. A reader who wants either should
	go to the family's own page, so this page does not grow a section every time a family is added.

	Reading a prediction is the annotated answer block rather than a passage, because the block is
	what a reader has to learn and it teaches itself once it is labelled.
-->
<script lang="ts">
	import AnnotatedAnswer from '$lib/components/AnnotatedAnswer.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { pageTitle, SITE_NAME } from '$lib/site';
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
			{SITE_NAME} is a collection of various machine learning models that predict statistics of future NBA games.
			Visit a specific model's about page to learn more about what each model predicts.
		</p>
	</section>

	<section id="reading">
		<h2>Reading a prediction</h2>

		<AnnotatedAnswer />
	</section>

	<section id="how">
		<h2>How it works</h2>
		<Notice>
			This section is not written yet.
		</Notice>
	</section>

	<section id="limitations">
		<h2>Limitations</h2>
		<Notice>
			This section is not written yet.
		</Notice>
	</section>
</div>

<style>
	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
</style>
