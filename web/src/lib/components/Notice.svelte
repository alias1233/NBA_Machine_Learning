<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		/** Neutral is an empty state, warning is something stale or partial, error is a failure. */
		tone?: 'neutral' | 'warning' | 'error';
		children: Snippet;
	};

	let { tone = 'neutral', children }: Props = $props();
</script>

<div class="panel {tone}">
	<p class="small">{@render children()}</p>
</div>

<style>
	.warning {
		background: var(--warn-wash);
		border: var(--rule-panel);
		border-color: var(--warn-border);
	}

	.error p {
		color: var(--under);
	}
</style>
