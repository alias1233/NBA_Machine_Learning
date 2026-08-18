<!--
	The printed band every page opens with.

	It is the site's own register: a plate in flat spot inks on saturated stock, registered with press
	crosses, running the full width of the screen with its printing held on the page column. The fixed
	header is printed on it rather than set above it, which is why the band takes the header's height
	back as its own top padding.

	What comes after the head, if anything, is given the band's whole width. The prediction pages put
	the night's board there, so the games are dealt on the same sheet the page is stamped on.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		/** The page's own heading, stamped. */
		title: string;
		/** One line saying what the page answers. Omitted where the heading says it all. */
		lede?: string;
		/** The one way out of the page, printed under the lede. */
		action?: Snippet;
		/** Anything given the band's full width, under the head. */
		extra?: Snippet;
	};

	let { title, lede = '', action, extra }: Props = $props();
</script>

<section class="band plate" class:extended={extra}>
	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>

	<div class="page head">
		<h1 class="plate-display">{title}</h1>

		<div class="said">
			{#if lede}
				<p class="lede measure">{lede}</p>
			{/if}

			{#if action}
				<div class="action">{@render action()}</div>
			{/if}
		</div>
	</div>

	{#if extra}
		{@render extra()}
	{/if}
</section>

<style>
	.band {
		position: relative;
		padding-block-end: var(--space-6);
	}

	/* A band carrying something of its own below the head hands the bottom edge to it. */
	.band.extended {
		padding-block-end: 0;
	}

	.head {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-items: start;
		gap: var(--space-3);
	}

	.said {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.lede {
		color: var(--plate-ink);
		font-size: var(--type-note);
	}

	/* A way out of the page is printed in the one ink rather than in the spot colour, which belongs to
	   the action a page leads with and not to a link beside its title. */
	.action {
		margin-block-start: var(--space-1);
		--plane-accent: var(--plate-ink);
	}

	.band.extended .head {
		padding-block-end: var(--space-6);
	}

	/*
	 * Wider: the stamp takes the leading column and everything said about it stands in the second,
	 * set on the stamp's last line. A title alone across a sheet this wide leaves most of the band
	 * empty, and a plate with nothing printed on two thirds of it is not a plate.
	 */
	@media (min-width: 64rem) {
		.head {
			grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
			align-items: end;
			column-gap: var(--space-7);
		}

		.head h1 {
			grid-row: 1 / -1;
		}

		.said {
			padding-block-end: var(--space-2);
		}
	}
</style>
