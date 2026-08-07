<!--
	The landing screen. One viewport, no scroll, and nothing on it but the name, one line, and the
	way in. See section 11.1.

	One backdrop block holds the whole screen. It carries a placed grid, and the words take cells of
	their own inside it, which is what keeps a tile off them at every width without measuring
	anything. R8.4 and R8.7.
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import { browser } from '$app/environment';

	import CollageTile from '$lib/components/CollageTile.svelte';
	import { TILES } from '$lib/collage';
	import { SITE_DESCRIPTION, SITE_NAME } from '$lib/site';

	const ENTERED = 'landing-entered';

	// The entrance plays once a browser session. The server cannot read sessionStorage, so it renders
	// the entrance and the browser cancels it on a return visit. Reading here rather than in onMount
	// is what keeps a click on the wordmark from showing a frame of it. R7.10.
	const entering = !browser || sessionStorage.getItem(ENTERED) === null;

	onMount(() => {
		sessionStorage.setItem(ENTERED, '1');
	});
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<meta
		name="description"
		content="The chance of every points, rebounds and assists total for an NBA player in an upcoming game."
	/>
</svelte:head>

<div class="block backdrop">
	{#each TILES as image, index (index)}
		<CollageTile {image} {index} {entering} />
	{/each}

	<!-- Everything here is block family, because the backdrop is a block. R3.3 and R11.3. -->
	<div class="words" class:entering>
		<h1 class="display">{SITE_NAME}</h1>
		<p>{SITE_DESCRIPTION}</p>

		<div class="actions">
			<a class="button button--lead" href="/models">Run a prediction</a>
			<a href="/about">How it works</a>
		</div>
	</div>
</div>

<style>
	/* Two rows of tiles with the words between them, which is all there is room for below 40rem. */
	.backdrop {
		display: grid;
		flex: 1;
		min-height: 0;
		gap: var(--collage-gap);
		grid-template-columns: repeat(3, minmax(0, 1fr));
		grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
		grid-template-areas:
			't1 t2 t3'
			'w  w  w'
			't4 t5 t6';
	}

	/*
	 * The words hold their cells and the four tile rows share whatever is left, so the collage gives
	 * up room before the words do and the screen stays one viewport. R6.6.
	 *
	 * The padding turns the grid gap into the --space-5 of clear backdrop R8.7 asks for between the
	 * nearest tile edge and the words.
	 */
	.words {
		grid-area: w;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-4);
		padding: var(--space-3);
		text-align: center;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: var(--space-5);
		margin-top: var(--space-2);
	}

	.actions a:not(.button) {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* The words arrive once the first tile has landed. R7.10. */
	.words.entering {
		animation: fade var(--motion-slow) var(--ease-in) var(--motion-entry) backwards;
	}

	/* Tiles 1 to 3 sit shoulder to shoulder and read as one group. Tiles 4 to 6 sit apart from it
	   and from each other, each aligned to a grid line the group already uses. R8.4. */
	@media (min-width: 40rem) {
		.backdrop {
			grid-template-columns: repeat(8, minmax(0, 1fr));
			grid-template-rows: repeat(2, minmax(0, 1fr)) auto auto repeat(2, minmax(0, 1fr));
			grid-template-areas:
				't4 t4 .  .  .  t1 t2 t2'
				'.  .  .  .  .  t1 t3 t3'
				'.  w  w  w  w  w  w  .'
				't5 w  w  w  w  w  w  .'
				't5 .  .  .  .  .  t6 t6'
				'.  .  .  .  .  .  t6 t6';
		}
	}

	@keyframes fade {
		from {
			opacity: 0;
		}
	}
</style>
