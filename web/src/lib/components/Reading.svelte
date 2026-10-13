<script lang="ts">
	import { flowingHeight } from '$lib/motion';

	import type { Snippet } from 'svelte';

	type Props = {
		/** True once there is a result to show. Until then the skeleton is shown. */
		answered: boolean;
		answer: Snippet;
		/** Placeholder with the same size as the result. */
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
	.reading {
		overflow: clip;
	}

	.swap {
		display: grid;
	}

	.swap > * {
		grid-area: 1 / 1;
		min-width: 0;
	}
</style>
