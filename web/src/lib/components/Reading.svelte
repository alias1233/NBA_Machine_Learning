<!--
	The surface an answer is read on, and the one place a skeleton gives way to one.

	Every reading is the same object whatever shape the answer takes: a surface holding reserved
	space at the size the answer will fill, then the answer itself in that space. The surface holds
	the height of whatever is in it, so the two flow into each other and nothing inside carries a
	motion of its own.

	The swap is a print rather than a replacement. The reserved space clears while the answer is
	struck onto it, so the two overlap in the one place instead of one appearing after the other has
	gone. That is why both stand in the same cell for those frames: the surface keeps its size while
	they trade, which is the same reason the two are drawn to the same size in the first place. The
	two are timed to hand over rather than to be quick, so the surface is never briefly empty between
	them.

	The strike is the site's impression and comes up out of register rather than travelling, so it
	can be printed inside a clipped edge without anything moving under it.
-->
<script lang="ts">
	import { appear, flowingHeight, MOTION } from '$lib/motion';

	import type { Snippet } from 'svelte';

	type Props = {
		/** True once there is an answer to draw. Anything else is reserved space. */
		answered: boolean;
		answer: Snippet;
		/** Reserved space at the size the answer will take, and never named. */
		skeleton: Snippet;
		/**
		 * True where the block stands for an answer rather than being one, which is the About page's
		 * annotated block. Nothing landed there, so nothing is printed, and the leader lines drawn to
		 * its parts are measured against a drawing that is not moving.
		 */
		example?: boolean;
	};

	let { answered, answer, skeleton, example = false }: Props = $props();
</script>

<div class="surface reading" use:flowingHeight>
	<div class="swap">
		{#if answered}
			<div class:printed={!example} out:appear={{ duration: MOTION }}>{@render answer()}</div>
		{:else}
			<div out:appear={{ duration: MOTION }}>{@render skeleton()}</div>
		{/if}
	</div>
</div>

<style>
	/* The surface holds the height, so what it holds is laid out one level in. */
	.reading {
		overflow: clip;
	}

	/* One cell, so the reserved space and the answer trade in the same place rather than one under
	   the other. */
	.swap {
		display: grid;
	}

	.swap > * {
		grid-area: 1 / 1;
		min-width: 0;
	}

	/* Held for a beat, so the impression comes up into space that is already clearing rather than
	   over one still standing at full strength. */
	.printed {
		animation: strike var(--motion-slow) var(--ease-in) 60ms backwards;
	}
</style>
