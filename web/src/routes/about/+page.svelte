<!--
	What the site is, and nothing about any one model.

	No model is explained here and no accuracy figure appears here. A reader who wants either is sent
	to the family's own page, so this page does not grow a section every time a family is added.

	The three bodies are placeholders. Writing them is the user's to settle.
-->
<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import { familyAboutPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	let { data } = $props();
</script>

<svelte:head>
	<title>{pageTitle('About')}</title>
	<meta
		name="description"
		content="What this site is, how to read a prediction, and what it does not do."
	/>
</svelte:head>

<div class="page">
	<h1 class="page-title">How it works</h1>

	<section>
		<h2>What this is</h2>
		<Notice>This section is not written yet.</Notice>
	</section>

	<section id="reading">
		<h2>Reading a prediction</h2>
		<Notice>This section is not written yet.</Notice>

		<!-- How a probability turns into odds is the same on every model, which is why it lives here.
		     How one particular model reaches that probability does not. -->
		<ul class="links">
			{#each data.families as family (family.name)}
				<li><a href={familyAboutPath(family)}>How this model works</a></li>
			{/each}
		</ul>
	</section>

	<section id="limits">
		<h2>What this is not</h2>
		<Notice>This section is not written yet.</Notice>
	</section>
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		scroll-margin-top: var(--space-8);
	}

	.links {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: 0;
		list-style: none;
	}

	.links a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}
</style>
