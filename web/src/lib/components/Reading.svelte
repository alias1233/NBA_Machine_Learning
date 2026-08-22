<!--
	The surface an answer is read on, and the one place a skeleton gives way to one.

	Every reading is the same object whatever shape the answer takes: a surface holding reserved
	space at the size the answer will fill, then the answer itself in that space. The surface holds
	the height of whatever is in it, so the two flow into each other and nothing inside carries a
	motion of its own.

	The reserved space and answer overlap in one cell, so the surface keeps its size while they trade.
	The answer block owns the arrival motion because it knows whether the result is the first one or a
	replacement. Keeping that decision out of this swap prevents two effects from playing at once.
-->
<script lang="ts">
	import { flowingHeight } from '$lib/motion';

	import type { Snippet } from 'svelte';

	type Props = {
		/** True once there is an answer to draw. Anything else is reserved space. */
		answered: boolean;
		answer: Snippet;
		/** Reserved space at the size the answer will take, and never named. */
		skeleton: Snippet;
	};

	let { answered, answer, skeleton }: Props = $props();
</script>

<div class="surface reading" use:flowingHeight>
	<div class="swap">
		{#if answered}
			<div>{@render answer()}</div>
		{:else}
			<div>{@render skeleton()}</div>
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
</style>
