<!--
	The shell every page sits in: the header, the page itself, and the footer. The wordmark and the
	tabs are rooted, so they sit in the same place on every page.

	The header is fixed and gets out of the way once the reader scrolls. Three things bring it back
	and nothing else: the top of the page, a pointer in the top --header-reveal-zone, and focus
	landing inside it.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { prefersReducedMotion } from 'svelte/motion';

	import '../app.css';

	import { longGameDay } from '$lib/games';
	import { MODELS_PATH, MODELS_SECTION, familyPath } from '$lib/models';
	import { SITE_NAME } from '$lib/site';

	let { children, data } = $props();

	const here = $derived(page.url.pathname);
	const home = $derived(here === '/');
	const onModels = $derived(here.startsWith('/models'));

	// Every entry in the menu leads to a prediction page, so a family with nothing to predict yet is
	// listed on the home page and not here.
	const predictable = $derived(data.families.filter((family) => family.published));

	const collectedThrough = $derived(
		data.health?.newest_stored_game ? longGameDay(data.health.newest_stored_game) : null
	);

	// The Models tab points at a section of the home page, so there the mark follows the reader down
	// the page rather than the address bar.
	let atModels = $state(false);

	$effect(() => {
		if (!home) {
			atModels = false;
			return;
		}

		const section = document.getElementById(MODELS_SECTION);
		if (!section) return;

		// Marked once the section has reached the middle of the viewport.
		const spy = new IntersectionObserver(([entry]) => (atModels = entry.isIntersecting), {
			rootMargin: '-45% 0px'
		});

		spy.observe(section);

		return () => spy.disconnect();
	});

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

	let scrollY = $state(0);
	let headerHeight = $state(0);
	let nearTop = $state(false);
	let holdingFocus = $state(false);
	let revealZone = $state(0);

	// It hides once the page has scrolled past half the header height, so a small scroll does not
	// take it away, and it returns at the very top rather than on the way back up.
	const hidden = $derived(scrollY > headerHeight / 2 && !nearTop && !holdingFocus);

	// A touch leaves its last position behind, which would hold the header open after a scroll that
	// started at the top of the screen. Only a pointer that hovers can reveal.
	function onPointerMove(event: PointerEvent) {
		if (event.pointerType === 'touch') return;

		const near = event.clientY <= revealZone;

		if (near !== nearTop) nearTop = near;
	}

	function onHeaderFocusOut(event: FocusEvent & { currentTarget: HTMLElement }) {
		holdingFocus = event.currentTarget.contains(event.relatedTarget as Node | null);
	}

	onMount(() => {
		const zone = getComputedStyle(document.documentElement).getPropertyValue('--header-reveal-zone');

		revealZone = parseFloat(zone);
	});

	// Pages cross-fade. A change within one page never does, because the reader did not ask to go
	// anywhere. Where the browser has no view transitions the navigation is simply instant, and
	// reduced motion opts out the same way rather than through a shorter animation.
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

<svelte:window bind:scrollY onpointermove={onPointerMove} />

<header
	class:hidden
	class:scrolled={scrollY > 0}
	bind:clientHeight={headerHeight}
	onfocusin={() => (holdingFocus = true)}
	onfocusout={onHeaderFocusOut}
>
	<div class="page masthead">
		<a class="wordmark" href="/">{SITE_NAME}</a>

		<nav>
			<ul class="tabs">
				<li>
					<a href="/" aria-current={home && !atModels ? 'page' : undefined}>Home</a>
				</li>

				<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
				<li
					class="menu"
					class:dismissed
					onkeydown={onMenuKeydown}
					onpointerleave={() => (dismissed = false)}
					onfocusout={onMenuFocusOut}
				>
					<a
						id="models-tab"
						href={MODELS_PATH}
						aria-current={onModels ? 'page' : atModels ? 'location' : undefined}
					>
						Models
					</a>

					{#if predictable.length > 0}
						<ul class="panel" aria-labelledby="models-tab">
							{#each predictable as family (family.name)}
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

<main>
	{@render children()}
</main>

<footer>
	<div class="page notes small muted">
		<p>Predictions are a model's estimate, published for information. This is not betting advice.</p>

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

<style>
	/* The chrome tone is what separates the header from the page, so it carries no rule. */
	header {
		position: fixed;
		z-index: 30;
		inset: 0 0 auto;
		background: var(--block);
		transition:
			translate var(--motion) var(--ease-in),
			box-shadow var(--motion-fast) var(--ease-in);
	}

	/* A header returning over scrolled content with no shadow reads as a strip cut out of the page
	   rather than as something above it. */
	header.scrolled {
		box-shadow: var(--shadow);
	}

	header.hidden {
		translate: 0 -100%;
		transition-timing-function: var(--ease-out);
	}

	/* One row at every width. The page reserves exactly this height, so the wordmark gives up room
	   rather than wrapping the header onto a second line. */
	.masthead {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding-block: var(--space-2);
	}

	.wordmark {
		display: flex;
		align-items: center;
		min-width: 0;
		min-height: var(--tap-target);
		overflow: hidden;
		color: var(--block-ink);
		text-decoration: none;
		white-space: nowrap;
	}

	nav {
		flex: none;
	}

	.tabs {
		display: flex;
		gap: var(--space-4);
		padding: 0;
		list-style: none;
	}

	.tabs > li {
		flex: none;
	}

	.tabs > li > a {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
		border-bottom: var(--rule-accent);
		border-bottom-color: transparent;
		color: var(--block-muted);
		font-size: var(--type-small);
		font-weight: 600;
		text-decoration: none;
		transition: color var(--motion-fast) var(--ease-in);
	}

	.tabs > li > a:hover,
	.tabs > li > a[aria-current] {
		color: var(--accent);
	}

	/* Accent text plus a rule, never colour alone. */
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

	/* A fixed header is out of flow, so the page reserves its height rather than shifting under it
	   when it hides. */
	main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		padding-block: calc(var(--header-height) + var(--space-5)) var(--space-8);
	}

	footer {
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

	@media (min-width: 40rem) {
		.masthead {
			gap: var(--space-5);
		}

		.tabs {
			gap: var(--space-5);
		}
	}
</style>
