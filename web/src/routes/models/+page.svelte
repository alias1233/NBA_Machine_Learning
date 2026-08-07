<!--
	Every model family. See section 11.2.

	This page does not list upcoming games. A game is only predictable by a particular family, and
	sending a reader from here into one with a game attached would silently pick a family for them.
	R11.6.

	The families come from the layout, so the header menu and this page are built from one list.
-->
<script lang="ts">
	import AdSlot from '$lib/components/AdSlot.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	let { data } = $props();
</script>

<svelte:head>
	<title>{pageTitle('Models')}</title>
	<meta
		name="description"
		content="Machine learning models that predict NBA outcomes before a game is played."
	/>
</svelte:head>

<div class="page sections">
	<section class="families">
		<h1 class="page-title">Models</h1>

		{#if data.families.length === 0}
			<Notice>No model is published right now.</Notice>
		{:else}
			{#each data.families as family (family.name)}
				<div class="block family">
					<!-- Reserves what the family graphic will take, so dropping one in shifts nothing. A
					     nested image area inside a block is a surface. R3.4. -->
					<div class="graphic surface" aria-hidden="true"></div>

					<div class="about">
						<h2 class="type-h3">{family.title}</h2>
						<p class="muted">{family.description}</p>
						<a class="button" href={familyPath(family)}>Predict</a>
					</div>
				</div>
			{/each}
		{/if}
	</section>

	<AdSlot place="modelsFooter" />
</div>

<style>
	.families {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.family {
		display: grid;
		gap: var(--space-5);
	}

	/* Square, like a game card, so a family reads in the same language as everything it leads to. */
	.graphic {
		aspect-ratio: var(--card-ratio);
	}

	.about {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	/* The button sits away from the description rather than under it, so the block reads as a card
	   with one way out of it. */
	.about .button {
		margin-top: var(--space-2);
	}

	/* The graphic moves beside the words once the block is wide enough to hold both. */
	@media (min-width: 40rem) {
		.family {
			grid-template-columns: calc(var(--space-8) * 2) 1fr;
			align-items: center;
		}
	}
</style>
