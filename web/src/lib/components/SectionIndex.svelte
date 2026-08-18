<!--
	What a page holds, listed.

	An explaining page is long and a reader usually came for one part of it, so the parts are named up
	front. On a narrow screen the list is a run of links across the top of the page. On a wide one it
	stands beside the sections and follows the reader down, in the column the text does not use.

	The anchors are the sections' own, so every entry is a link to somewhere already on the page and
	travels to it rather than jumping.
-->
<script lang="ts">
	type Props = {
		/** Each section's anchor and its heading, in the order the page sets them. */
		sections: string[][];
		label: string;
	};

	let { sections, label }: Props = $props();
</script>

<nav class="index" aria-label={label}>
	<ul>
		{#each sections as [anchor, heading] (anchor)}
			<li><a class="small text-link" href="#{anchor}">{heading}</a></li>
		{/each}
	</ul>
</nav>

<style>
	.index ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0 var(--space-4);
		margin: 0;
		padding: 0;
		list-style: none;
		border-block: var(--rule-panel);
	}

	.index a {
		color: var(--ink-muted);
		text-decoration: none;
		transition: color var(--motion-fast) var(--ease-in);
	}

	.index a:hover {
		color: var(--accent);
	}

	@media (min-width: 64rem) {
		.index {
			position: sticky;
			top: calc(var(--header-height) + var(--space-5));
		}

		.index ul {
			flex-direction: column;
			padding-inline-start: var(--space-3);
			border-block: none;
			border-left: var(--rule-panel);
		}
	}
</style>
