<!--
	The landing screen. One viewport, no scroll, and nothing on it but the name, one line, and the way
	in. See section 11.1.

	The collage sits in a band above the words and a band below them, so no tile can overlap them at
	any width or at any point in its float. R8.7 is held by the grid rather than by measurement.
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import { browser } from '$app/environment';

	import Collage from '$lib/components/Collage.svelte';
	import { SITE_DESCRIPTION, SITE_NAME } from '$lib/site';

	const ENTERED = 'landing-entered';

	// The entrance plays once a browser session. The server cannot read sessionStorage, so it renders
	// the entrance and the browser cancels it on a return visit. Reading here rather than in onMount
	// is what keeps a click on the wordmark from showing a frame of it. R7.7.
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

<div class="screen">
	<Collage band="top" {entering} />

	<div class="words" class:entering>
		<h1 class="display">{SITE_NAME}</h1>
		<p>{SITE_DESCRIPTION}</p>

		<div class="actions">
			<a class="button button--lead" href="/models">Run a prediction</a>
			<a href="/about">How it works</a>
		</div>
	</div>

	<Collage band="bottom" {entering} />
</div>

<style>
	/* The two collage rows give up room before the words do, which is what holds the screen to one
	   viewport at 320x568 and at 200 percent zoom. R6.6 and R12.10. */
	.screen {
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
		gap: var(--space-5);
		flex: 1;
		min-height: 0;
		padding: var(--space-5) var(--space-4);
	}

	.words {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		width: 100%;
		max-width: calc(var(--space-8) * 8);
		margin-inline: auto;
		text-align: center;
	}

	.words p {
		margin-inline: auto;
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

	/* The words arrive once the first tile has landed. R7.7. */
	.words.entering {
		animation: fade var(--motion-slow) var(--ease-in) var(--motion-entry) backwards;
	}

	@keyframes fade {
		from {
			opacity: 0;
		}
	}
</style>
