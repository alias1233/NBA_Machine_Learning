<!--
	The shape every prediction page takes, whichever family it is for.

	It has two shapes. Before the first prediction it is one centred column of controls and nothing
	else, because a reader who has not asked for anything should not be looking at an empty box. On
	the first submit the answer column opens beside them, line first and then widening, and never
	closes.

	What differs between families is what the reader has to choose and how the answer names itself, so
	those arrive as the two snippets. Everything here is the layout the design document sets, which is
	the same for all of them.
-->
<script lang="ts">
	import { tick } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';
	import { MediaQuery } from 'svelte/reactivity';

	import AdSlot from '$lib/components/AdSlot.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { MOTION_REVEAL, MOTION_SLOW, appear, flow, flowingHeight } from '$lib/motion';
	import { scrollIntoViewIfOffScreen } from '$lib/scroll';
	import { pageTitle } from '$lib/site';

	import type { Snippet } from 'svelte';

	type Props = {
		title: string;
		/** One sentence, for a search result and a shared link. */
		description: string;
		/** The family's own page, linked under the title before a reader asks for a number. */
		aboutHref: string;
		/** False when the service offers nothing this page can draw, which is its empty state. */
		hasModels: boolean;
		/** True when the page loaded with an answer already, so the column opens with no motion. */
		answered: boolean;
		controls: Snippet;
		/** One element. It holds the answer, the skeleton and a failure alike. */
		result: Snippet;
	};

	let { title, description, aboutHref, hasModels, answered, controls, result }: Props = $props();

	let answerColumn = $state<HTMLElement>();

	// svelte-ignore state_referenced_locally
	let opened = $state(answered);
	// svelte-ignore state_referenced_locally
	let widened = $state(answered);

	// The width two columns need, which app.css sets the layout at. Above it the answer opens
	// sideways, below it there is nowhere to the side and its own height is what opens.
	const sideways = new MediaQuery('min-width: 64rem', false);

	/**
	 * Opens the answer column, once, for a reader who pressed the button, and walks them to it.
	 *
	 * The line grows first and then widens into the column, so the press gets an answer of its own
	 * straight away rather than waiting on the service. Nothing is awaited by the caller, because the
	 * request it is answering goes out in the same breath.
	 */
	export async function reveal(): Promise<void> {
		const revealing = opened ? 0 : MOTION_REVEAL;

		if (!opened) {
			opened = true;

			if (prefersReducedMotion.current) widened = true;
			else setTimeout(() => (widened = true), MOTION_SLOW);
		}

		// The column is created by the line above, so it has to exist before it can be scrolled to.
		await tick();
		scrollIntoViewIfOffScreen(answerColumn, 'start', revealing);
	}
</script>

<svelte:head>
	<title>{pageTitle(title)}</title>
	<meta name="description" content={description} />
</svelte:head>

<div class="page sections" class:page--wide={widened}>
	<div class="work" class:wide={widened}>
		<div class="title">
			<h1 class="page-title">{title}</h1>

			<!-- How the number is reached, before a reader asks for one. -->
			<a class="small" href={aboutHref}>How this model works</a>
		</div>

		{#if !hasModels}
			<!-- With nothing published there is nothing to offer, so the page is this and no more. -->
			<Notice>No model is published right now.</Notice>
		{:else}
			<div class="columns sections">
				<div class="controls sections">
					{@render controls()}
				</div>

				{#if opened}
					<!-- The line that grows out of the column's future left edge, phase one of the reveal.
					     It fades as the column takes its width, because the edge it marks moves off it. -->
					{#if !widened}
						<div class="opening-line" out:appear aria-hidden="true"></div>
					{/if}

					<!-- Two columns open sideways. One column has nowhere to the side, so the answer
					     arrives at the bottom and opens by its own height instead. -->
					<div
						class="answer"
						class:narrow={!widened}
						in:flow={{ duration: sideways.current ? 0 : MOTION_REVEAL }}
						bind:this={answerColumn}
					>
						<!-- One box for the skeleton, the answer and a failure alike, so the page never jumps
						     once the column is open. It holds the height of whichever is in it, so the
						     skeleton flows into the answer rather than being replaced by it. -->
						<div class="answer-body" use:flowingHeight>
							{@render result()}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<AdSlot place="modelBelowResult" />
</div>

<style>
	/* The page takes its wide cap as the column widens, which is the second half of the reveal. */
	.page {
		transition: max-width var(--motion-reveal) var(--ease-in-out);
	}

	/* Whatever is in the column decides its height, and the swap from the skeleton to the answer
	   flows between the two rather than landing in one frame. The height itself is the action's. */
	.answer-body {
		overflow: clip;
	}

	/* One narrow column, centred, until an answer opens beside it. The width is explicit because an
	   auto margin on a flex item turns off its stretch and leaves it shrink to fit. */
	.work {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		width: 100%;
		max-width: var(--control-column);
		margin-inline: auto;
	}

	.title {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
	}

	.title a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* Below 64rem there is no column and no reveal. The answer arrives at the bottom of the one
	   column and the page is scrolled to it. */
	.opening-line {
		display: none;
	}

	@media (min-width: 64rem) {
		/* The controls are moved by the reveal, never squeezed, so they hold this width throughout. */
		.work {
			transition: max-width var(--motion-reveal) var(--ease-in-out);
		}

		.work.wide {
			max-width: var(--content-width-wide);
		}

		.columns {
			position: relative;
			flex-direction: row;
			align-items: flex-start;
			gap: var(--space-6);
		}

		.controls {
			flex: 1 1 auto;
			min-width: 0;
			max-width: var(--control-column);
		}

		/*
		 * Phase two. The column takes its width and the page takes its wide cap together, which
		 * pushes the controls left as the answer opens. It is clipped, so the skeleton is already
		 * inside it on the way out rather than reflowing behind it.
		 */
		.answer {
			flex: 0 0 var(--answer-column);
			min-width: 0;
			overflow: clip;
			transition: flex-basis var(--motion-reveal) var(--ease-in-out);
		}

		.answer.narrow {
			flex-basis: 0;
		}

		.answer-body {
			width: var(--answer-column);
		}

		/* Phase one, at the column's future left edge, which is the right edge of the row while the
		   column has no width yet. */
		.opening-line {
			display: block;
			position: absolute;
			inset: 0 0 0 auto;
			width: 2px;
			background: var(--accent);
			animation: line-grow var(--motion-slow) var(--ease-in);
		}
	}

	@keyframes line-grow {
		from {
			transform: scaleY(0);
		}
	}
</style>
