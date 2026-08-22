<script lang="ts">
	import { longDate, SITE_UPDATED_AT } from '$lib/site';

	const date = longDate(SITE_UPDATED_AT);
</script>

<p class="editorial-meta small">
	<span><time datetime={SITE_UPDATED_AT}>Published {date}</time></span>
	<span><time datetime={SITE_UPDATED_AT}>Updated {date}</time></span>
</p>

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
