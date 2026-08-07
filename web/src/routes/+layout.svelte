<!--
	The shell every page sits in: the header, the page itself, and the footer.

	The landing screen is the one exception and section 11.1 spells it out. It drops the header's
	background, rule and wordmark so only the tabs float over the collage, and it carries no footer,
	because it is one screen with one message.
-->
<script lang="ts">
	import '../app.css';

	import { onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { prefersReducedMotion } from 'svelte/motion';

	import { longGameDay } from '$lib/games';
	import { familyPath } from '$lib/models';
	import { SITE_NAME } from '$lib/site';

	let { children, data } = $props();

	const here = $derived(page.url.pathname);
	const landing = $derived(here === '/');
	const onModels = $derived(here.startsWith('/models'));

	const collectedThrough = $derived(
		data.health?.newest_stored_game ? longGameDay(data.health.newest_stored_game) : null
	);

	// The menu opens on hover and on focus. Escape closes it until the pointer or focus leaves.
	let dismissed = $state(false);

	function onMenuKeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape') return;

		dismissed = true;
		(event.currentTarget as HTMLElement).querySelector('a')?.focus();
	}

	// Escape leaves focus on the tab, which is still inside the menu, so only a real exit reopens it.
	function onMenuFocusOut(event: FocusEvent) {
		const menu = event.currentTarget as HTMLElement;

		if (!menu.contains(event.relatedTarget as Node | null)) dismissed = false;
	}

	// Pages cross-fade. A change within one page never does, because the reader did not ask to go
	// anywhere. Where the browser has no view transitions the navigation is simply instant, and
	// reduced motion opts out the same way rather than through a shorter animation. R7.5 and R7.6.
	onNavigate((navigation) => {
		const samePage = navigation.from?.url.pathname === navigation.to?.url.pathname;

		if (samePage || !document.startViewTransition || prefersReducedMotion.current) return;

		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});
</script>

<header class:landing>
	<div class="page masthead">
		<!-- The landing screen already prints the name at display size, so it drops the wordmark. -->
		{#if !landing}
			<a class="wordmark" href="/">{SITE_NAME}</a>
		{/if}

		<nav>
			<ul class="tabs">
				<li>
					<a href="/" aria-current={landing ? 'page' : undefined}>Home</a>
				</li>

				<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
				<li
					class="menu"
					class:dismissed
					onkeydown={onMenuKeydown}
					onpointerleave={() => (dismissed = false)}
					onfocusout={onMenuFocusOut}
				>
					<a id="models-tab" href="/models" aria-current={onModels ? 'page' : undefined}>Models</a>

					{#if data.families.length > 0}
						<ul class="panel" aria-labelledby="models-tab">
							{#each data.families as family (family.name)}
								<li><a href={familyPath(family)}>{family.title}</a></li>
							{/each}
						</ul>
					{/if}
				</li>

				<li>
					<a href="/about" aria-current={here === '/about' ? 'page' : undefined}>About</a>
				</li>
			</ul>
		</nav>
	</div>
</header>

<main class:landing>
	{@render children()}
</main>

{#if !landing}
	<footer>
		<div class="page notes small muted">
			<p>
				Predictions are a model's estimate, published for information. This is not betting advice.
			</p>

			{#if collectedThrough}
				<p>Built from games played through {collectedThrough}.</p>
			{:else}
				<p>The prediction service is not answering.</p>
			{/if}

			<ul class="links">
				<li><a href="/about">About</a></li>
				<li><a href="/privacy">Privacy</a></li>
			</ul>
		</div>
	</footer>
{/if}

<style>
	header {
		background: var(--page);
		border-bottom: var(--rule);
	}

	/* Nothing behind the tabs, so they read as floating over the collage. R10.4. */
	header.landing {
		background: none;
		border-bottom: none;
	}

	.masthead {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3) var(--space-5);
		padding-block: var(--space-2);
	}

	.wordmark {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
		color: var(--ink);
		text-decoration: none;
	}

	/* Keeps the tabs on the right whether or not the wordmark is beside them. */
	nav {
		margin-left: auto;
	}

	.tabs {
		display: flex;
		gap: var(--space-5);
		padding: 0;
		list-style: none;
	}

	.tabs > li > a {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
		border-bottom: var(--rule-accent);
		border-bottom-color: transparent;
		color: var(--ink-muted);
		font-size: var(--type-small);
		font-weight: 600;
		text-decoration: none;
		transition: color var(--motion-fast) var(--ease-in);
	}

	.tabs > li > a:hover,
	.tabs > li > a[aria-current] {
		color: var(--accent);
	}

	/* Accent text plus a rule, never colour alone. R10.1. */
	.tabs > li > a[aria-current] {
		border-bottom-color: var(--accent);
	}

	.menu {
		position: relative;
	}

	/* Centred on the Models tab, not offset from it. A raised panel, so it carries the shadow. */
	.menu > ul {
		position: absolute;
		z-index: 20;
		top: 100%;
		left: 50%;
		translate: -50% 0;
		visibility: hidden;
		opacity: 0;
		min-width: max-content;
		padding: var(--space-2);
		list-style: none;
		box-shadow: var(--shadow);
		transition:
			opacity var(--motion) var(--ease-in),
			visibility var(--motion);
	}

	.menu > ul a {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
		padding-inline: var(--control-padding-x);
		border-radius: var(--radius);
		color: var(--ink);
		font-size: var(--type-small);
		text-decoration: none;
		white-space: nowrap;
	}

	.menu > ul a:hover,
	.menu > ul a:focus-visible {
		background: var(--surface);
		color: var(--accent);
	}

	/* No hover on a touch device, so the tab is the whole control and the menu never opens. */
	@media (hover: hover) {
		.menu:hover > ul,
		.menu:focus-within > ul {
			visibility: visible;
			opacity: 1;
		}

		.menu.dismissed > ul {
			visibility: hidden;
			opacity: 0;
		}
	}

	main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		padding-block: var(--space-5) var(--space-8);
	}

	/* The landing screen fills what is left of the viewport instead of ending in page space. */
	main.landing {
		padding-block: 0;
	}

	footer {
		background: var(--page);
		border-top: var(--rule);
	}

	.notes {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding-block: var(--space-4);
	}

	.links {
		display: flex;
		gap: var(--space-4);
		padding: 0;
		list-style: none;
	}

	.links a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	@media (min-width: 64rem) {
		header {
			position: sticky;
			top: 0;
			z-index: 30;
		}

		/* The landing screen never scrolls, so nothing there needs to stick. */
		header.landing {
			position: static;
		}
	}
</style>
