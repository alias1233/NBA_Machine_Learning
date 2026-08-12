<!--
	The shell every page sits in: the header, the page itself, and the footer. The wordmark and the
	tabs are rooted, so they sit in the same place on every page.

	The header is fixed and gets out of the way once the reader scrolls. Five things bring it back and
	nothing else: the top of the page, a pointer in the top --header-reveal-zone, a scroll back up
	where there is no pointer, the models menu standing open, and keyboard focus landing inside it.

	The models menu opens on hover. A touch device has none, so there the first tap on the tab opens
	it and the second follows the tab.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { afterNavigate, onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { prefersReducedMotion } from 'svelte/motion';
	import { MediaQuery } from 'svelte/reactivity';

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

	// A device that can hover opens the menu by hovering, which app.css does on its own. One that
	// cannot has the tab open it, so the menu is reachable without a pointer.
	const canHover = new MediaQuery('hover: hover', true);

	let overMenu = $state(false);
	let revealed = $state(false);

	function onMenuPointerLeave() {
		overMenu = false;
	}

	/**
	 * The entry for the page the reader is already on leaves it exactly as it stands.
	 *
	 * A prediction page holds an answer and everything that was asked for it, all of it in the
	 * address bar, and the entry names the bare page, so following it would throw the lot away.
	 */
	function onFamilyEntry(event: MouseEvent, path: string) {
		if (here !== path) return;

		event.preventDefault();
		revealed = false;
	}

	/** The first tap opens the menu. The second is the tab doing what it says, so the menu is done. */
	function onModelsTab(event: MouseEvent) {
		if (canHover.current) return;

		if (revealed) {
			revealed = false;
			return;
		}

		event.preventDefault();
		revealed = true;
	}

	let masthead = $state<HTMLElement>();
	let menuRoot = $state<HTMLElement>();
	let menuList = $state<HTMLElement>();
	let menuNudge = $state(0);
	let viewportWidth = $state(0);

	// A press anywhere else puts the menu away, the same as a pointer leaving it.
	$effect(() => {
		if (!revealed) return;

		const closeOutside = (event: PointerEvent) => {
			if (!menuRoot?.contains(event.target as Node)) revealed = false;
		};

		document.addEventListener('pointerdown', closeOutside);

		return () => document.removeEventListener('pointerdown', closeOutside);
	});

	// Centred on its tab, unless the tab sits close enough to the edge that centring would put the
	// menu past the page gutter. Then it moves left by exactly what would have been cut off. A
	// hidden menu is still laid out, so this measures whatever the menu is doing.
	$effect(() => {
		// Read so a resize and a new family both re-measure.
		viewportWidth;
		predictable.length;

		if (!masthead || !menuRoot || !menuList) return;

		const gutter = parseFloat(getComputedStyle(masthead).paddingRight);
		const edge = masthead.getBoundingClientRect().right - gutter;
		const centre = menuRoot.getBoundingClientRect().left + menuRoot.offsetWidth / 2;

		menuNudge = Math.max(centre + menuList.offsetWidth / 2 - edge, 0);
	});

	let scrollY = $state(0);
	let headerHeight = $state(0);
	let nearTop = $state(false);
	let holdingFocus = $state(false);
	let scrolledUp = $state(false);
	let revealZone = $state(0);

	// It hides once the page has scrolled past half the header height, so a small scroll does not
	// take it away. The menu hangs below the reveal zone, so an open one holds the header as well,
	// and so does keyboard focus, because a hidden header cannot be scrolled to.
	const hidden = $derived(
		scrollY > headerHeight / 2 &&
			!nearTop &&
			!scrolledUp &&
			!overMenu &&
			!revealed &&
			!holdingFocus
	);

	/** Below this a move is jitter rather than a direction. */
	const SCROLL_STEP = 8;

	let lastScroll = 0;

	function onScroll() {
		const moved = window.scrollY - lastScroll;

		if (Math.abs(moved) < SCROLL_STEP) return;

		lastScroll = window.scrollY;

		// Scrolling on puts the header away whatever was holding it, a tapped menu included.
		if (moved > 0) {
			scrolledUp = false;
			revealed = false;
			return;
		}

		// A reader with no pointer has no top strip to reach into, so scrolling back up is the only
		// way they can ask for the header.
		scrolledUp = !canHover.current;
	}

	// A touch leaves its last position behind, which would hold the header open after a scroll that
	// started at the top of the screen. Only a pointer that hovers can reveal.
	function onPointerMove(event: PointerEvent) {
		if (event.pointerType === 'touch') return;

		const near = event.clientY <= revealZone;

		if (near !== nearTop) nearTop = near;
	}

	// A press focuses what it lands on, and a header held open by that would stay down after the
	// pointer had left it. A keyboard focus draws a ring, so only that has to keep the header
	// reachable.
	function onHeaderFocusIn(event: FocusEvent) {
		holdingFocus = (event.target as Element).matches(':focus-visible');
	}

	function onHeaderFocusOut(event: FocusEvent & { currentTarget: HTMLElement }) {
		holdingFocus = event.currentTarget.contains(event.relatedTarget as Node | null);
	}

	onMount(() => {
		const zone = getComputedStyle(document.documentElement).getPropertyValue('--header-reveal-zone');

		revealZone = parseFloat(zone);
		lastScroll = window.scrollY;
	});

	// Pages cross-fade. A change within one page never does, because the reader did not ask to go
	// anywhere. Where the browser has no view transitions the navigation is simply instant, and
	// reduced motion opts out the same way rather than through a shorter animation.
	//
	// A link to a section of the page already shown travels to it, which app.css does. Arriving
	// from another page lands on the section instead, because a scroll running under the cross-fade
	// would jump the moment the fade ended.
	onNavigate((navigation) => {
		const samePage = navigation.from?.url.pathname === navigation.to?.url.pathname;

		document.documentElement.classList.toggle('arriving', !samePage);

		if (samePage || !document.startViewTransition || prefersReducedMotion.current) return;

		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});

	// The scroll has already been made by the time this runs, so the page travels again from here.
	// A menu the reader tapped open has been answered by arriving somewhere, so it closes, and the
	// direction starts again from where the new page landed rather than from the last one.
	afterNavigate(() => {
		document.documentElement.classList.remove('arriving');
		revealed = false;
		scrolledUp = false;
		lastScroll = window.scrollY;
	});
</script>

<svelte:window
	bind:scrollY
	bind:innerWidth={viewportWidth}
	onscroll={onScroll}
	onpointermove={onPointerMove}
/>

<header
	class:hidden
	class:scrolled={scrollY > 0}
	bind:clientHeight={headerHeight}
	onfocusin={onHeaderFocusIn}
	onfocusout={onHeaderFocusOut}
>
	<div class="page masthead" bind:this={masthead}>
		<a class="wordmark" href="/">{SITE_NAME}</a>

		<nav>
			<ul class="tabs">
				<li>
					<a href="/" aria-current={home && !atModels ? 'page' : undefined}>Home</a>
				</li>

				<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
				<li
					class="menu"
					class:revealed
					style:--menu-nudge="{menuNudge}px"
					bind:this={menuRoot}
					onpointerenter={(event) => (overMenu = event.pointerType !== 'touch')}
					onpointerleave={onMenuPointerLeave}
				>
					<a
						id="models-tab"
						href={MODELS_PATH}
						aria-expanded={canHover.current ? undefined : revealed}
						aria-current={onModels ? 'page' : atModels ? 'location' : undefined}
						onclick={onModelsTab}
					>
						Models
					</a>

					{#if predictable.length > 0}
						<ul class="panel" aria-labelledby="models-tab" bind:this={menuList}>
							{#each predictable as family (family.name)}
								{@const path = familyPath(family)}
								<li>
									<a
										href={path}
										aria-current={here === path ? 'page' : undefined}
										onclick={(event) => onFamilyEntry(event, path)}
									>
										{family.title}
									</a>
								</li>
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
	/* The block tone is what separates the header from the page, so it carries no rule. Everything
	   drawn on it comes from the block family, the menu below it excepted, which is a panel sitting
	   on the page. */
	header {
		position: fixed;
		z-index: 30;
		inset: 0 0 auto;
		background: var(--block);
		--plane-accent: var(--accent-block);
		--plane-accent-on: var(--block);
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

	/* A tab carries its own padding, so an open one can be boxed without moving the row. The end of
	   the row gives that padding back, which keeps the last tab's text on the page gutter. */
	.tabs {
		display: flex;
		gap: var(--space-2);
		margin-inline-end: calc(var(--space-2) * -1);
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
		padding-inline: var(--space-2);
		border-bottom: var(--rule-accent);
		border-bottom-color: transparent;
		color: var(--block-muted);
		font-size: var(--type-small);
		font-weight: 600;
		text-decoration: none;
		transition:
			background var(--motion-fast) var(--ease-in),
			color var(--motion-fast) var(--ease-in);
	}

	.tabs > li > a:hover,
	.tabs > li > a[aria-current] {
		color: var(--plane-accent);
	}

	/* Accent text plus a rule, never colour alone. */
	.tabs > li > a[aria-current] {
		border-bottom-color: var(--plane-accent);
	}

	.menu {
		position: relative;
	}

	/* A tap opens the menu and the next one follows the tab, which is two jobs and no hover to tell
	   them apart. The open tab is boxed, so the second tap reads as a different press. */
	.menu.revealed > a {
		background: var(--hairline-block);
		border-radius: var(--radius);
	}

	/* Centred on the Models tab, and moved left by whatever centring would have hung past the page
	   gutter. A raised panel, so it carries the shadow. */
	.menu > ul {
		position: absolute;
		z-index: 20;
		top: 100%;
		left: 50%;
		translate: calc(-50% - var(--menu-nudge, 0px)) 0;
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

	/* The entry for the page the reader is already on. It leads nowhere, so it is marked with a rule
	   down its leading edge rather than underlined, which is what a link to somewhere else looks
	   like. */
	.menu > ul a[aria-current] {
		border-left: var(--rule-accent);
		background: var(--surface);
		color: var(--accent);
		cursor: default;
	}

	/* Open by hover where there is one, by the first tap on the tab where there is not, and by
	   keyboard focus either way. Keyboard focus rather than any focus, because a tab that keeps
	   focus after a tap would leave the menu standing over the page it just went to. */
	.menu.revealed > ul,
	.menu:has(:focus-visible) > ul {
		visibility: visible;
		opacity: 1;
	}

	@media (hover: hover) {
		.menu:hover > ul {
			visibility: visible;
			opacity: 1;
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
			gap: var(--space-3);
		}
	}
</style>
