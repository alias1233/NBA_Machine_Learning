<script lang="ts">
	import { datesOf } from '$lib/pages';
	import { longDate } from '$lib/site';

	type Props = {
		/** Path of the page these dates are for. */
		path: string;
	};

	let { path }: Props = $props();

	const dates = $derived(datesOf(path));
</script>

{#if dates}
	<p class="editorial-meta small">
		<span><time datetime={dates.published}>Published {longDate(dates.published)}</time></span>
		<span><time datetime={dates.updated}>Updated {longDate(dates.updated)}</time></span>
	</p>
{/if}

<style>
	.editorial-meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-4);
		padding-block: var(--space-3);
		border-block: var(--rule-panel);
	}

	.editorial-meta span + span::before {
		margin-inline-end: var(--space-4);
		color: var(--ink-muted);
		content: '•';
	}

	@media (width < 32rem) {
		.editorial-meta span + span::before {
			content: '';
		}
	}
</style>
