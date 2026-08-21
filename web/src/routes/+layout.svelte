<!--
	The shell every page sits in: the header, the page itself, and the footer. The wordmark and the
	tabs are rooted, so they sit in the same place on every page.

	Every page opens with a printed plate band and the header is printed on it rather than set above
	it, so the top of the screen is one object. Once the reader has scrolled it detaches and becomes a
	plate strip carrying the shadow, which is the one time it is a thing of its own.

	It is fixed and gets out of the way once the reader scrolls. Five things bring it back and nothing
	else: the top of the page, a pointer in the top --header-reveal-zone, a scroll back up where there
	is no pointer, the models menu standing open, and keyboard focus landing inside it.

	On the home page the header is a copy of the one printed on the hero. It shares the hero's
	scroll-driven movement until the Models section reaches the screen, then resumes the normal fixed
	header behavior without leaving two bars on screen.

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
	import { MODELS_PATH, MODELS_SECTION, familyPath, plateOf } from '$lib/models';
	import { SITE_NAME } from '$lib/site';
	import { ADS_ENABLED } from '$lib/ads.js'

	let { children, data } = $props();

	const here = $derived(page.url.pathname);
	const home = $derived(here === '/');
	const onModels = $derived(here.startsWith('/models'));

	// Which stock this page is printed on. It is set on the header as well as the page, because the
	// header is printed on the band under it and takes that ground once it detaches.
	const plate = $derived(plateOf(here));

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

	type HeaderRefs = {
		masthead?: HTMLElement;
		menuRoot?: HTMLElement;
		menuList?: HTMLElement;
	};

	let heroRefs = $state<HeaderRefs>({});
	let headerRefs = $state<HeaderRefs>({});
	let pastHero = $state(false);
	const activeRefs = $derived(home && !pastHero ? heroRefs : headerRefs);
	let menuNudge = $state(0);
	let viewportWidth = $state(0);

	// A press anywhere else puts the menu away, the same as a pointer leaving it.
	$effect(() => {
		if (!revealed) return;

		const closeOutside = (event: PointerEvent) => {
			if (!activeRefs.menuRoot?.contains(event.target as Node)) revealed = false;
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

		if (!activeRefs.masthead || !activeRefs.menuRoot || !activeRefs.menuList) return;

		const gutter = parseFloat(getComputedStyle(activeRefs.masthead).paddingRight);
		const edge = activeRefs.masthead.getBoundingClientRect().right - gutter;
		const centre = activeRefs.menuRoot.getBoundingClientRect().left + activeRefs.menuRoot.offsetWidth / 2;

		menuNudge = Math.max(centre + activeRefs.menuList.offsetWidth / 2 - edge, 0);
	});

	let scrollY = $state(0);
	let headerHeight = $state(0);
	let nearTop = $state(false);
	let holdingFocus = $state(false);
	let scrolledUp = $state(false);
	let revealZone = $state(0);
	let arrivingAtModels = $state(false);
	/* The home header belongs to the hero until the Models section takes over the viewport. */
	function syncPastHero() {
		const models = document.getElementById(MODELS_SECTION);

		pastHero = home && !!models && models.getBoundingClientRect().top <= 0;
	}

	// It hides once the page has scrolled past half the header height, so a small scroll does not
	// take it away. The menu hangs below the reveal zone, so an open one holds the header as well,
	// and so does keyboard focus, because a hidden header cannot be scrolled to.
	const hidden = $derived(
		holdingFocus
			? false
			: scrollY > headerHeight / 2 && !nearTop && !scrolledUp && !overMenu && !revealed
	);

	/** Below this a move is jitter rather than a direction. */
	const SCROLL_STEP = 8;

	let lastScroll = 0;

	function onScroll() {
		syncPastHero();

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
		syncPastHero();
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
		const destination = navigation.to?.url;
		arrivingAtModels =
			!samePage &&
			destination?.pathname === '/' &&
			destination.hash === `#${MODELS_SECTION}`;

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
		syncPastHero();
		arrivingAtModels = false;
	});
</script>

<svelte:window
	bind:scrollY
	bind:innerWidth={viewportWidth}
	onscroll={onScroll}
	onpointermove={onPointerMove}
/>

<!--
	THESIS: The model's answer is printed and fixed; the reader's question is drawn on top of it.
	This surface refuses the category's dark odds-board and its cream-and-serif opposite alike.
	OWN-WORLD: A saturated ink-blue plate (#013278) printed flat in bone (#ece3d1) and one spot
	orange (#f35411), registered with press crosses and a plate number, under a clear acetate sheet
	carrying wet-erase magenta (#f1589a) marks. Sharp corners everywhere. Mono for every figure.
	STORY: A visitor sees six real answers the site drew this morning, picks one by hand, drags a
	line across it, and learns that the answer is a shape rather than a number.
	FIRST VIEWPORT: Printed name and one line top left; tonight's samples as a grid of small hairline
	plates lower left, one ringed in grease pencil; the ringed sample's full distribution, its line
	handle and three printed odds boxes on the acetate to the right, with the orange action under it.
	FORM: The Coach's Acetate, candidate 7 of the grounded list, seed key 03ae8ebd.
	FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the
	verdict, DESIGN.md, and every shipping raster carrying its provenance.
-->
<!-- The first thing focus reaches, and the one way past a header that is holding itself away. -->
<a class="skip button" href="#content">Skip to content</a>

{#snippet masthead(modelsTabId: string, refs: HeaderRefs)}
	{@const ownsMenu = refs === activeRefs}
	<div class="page masthead" bind:this={refs.masthead}>
		<a class="wordmark" href="/">{SITE_NAME}</a>

		<nav>
			<ul class="tabs">
				<li>
					<a href="/" aria-current={home && !atModels ? 'page' : undefined}>Home</a>
				</li>

				<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
				<li
					class="menu"
					class:revealed={revealed && ownsMenu}
					style:--menu-nudge="{menuNudge}px"
					bind:this={refs.menuRoot}
					onpointerenter={(event) => (overMenu = event.pointerType !== 'touch')}
					onpointerleave={onMenuPointerLeave}
				>
					<a
						id={modelsTabId}
						href={MODELS_PATH}
						aria-expanded={canHover.current ? undefined : revealed && ownsMenu}
						aria-current={onModels ? 'page' : atModels ? 'location' : undefined}
						onclick={onModelsTab}
					>
						Models
					</a>

					<!-- A slip of the same plate, so the menu is part of the printing above it rather than
					     a page-coloured card floating over it. Each family says what it answers, because a
					     title alone leaves the reader to open all three to find out. -->
					{#if predictable.length > 0}
						<ul aria-labelledby={modelsTabId} bind:this={refs.menuList}>
							{#each predictable as family (family.name)}
								{@const path = familyPath(family)}
								<li>
									<a
										href={path}
										aria-current={here === path ? 'page' : undefined}
										onclick={(event) => onFamilyEntry(event, path)}
									>
										<span class="entry-title">{family.title}</span>
										<span class="entry-note small">{family.description}</span>
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
{/snippet}

{#if home}
	<!-- The hero owns this copy. It stays on the hero timeline until that paper has receded. -->
	<header
		class="plate home-header"
		class:neutral-page={!plate}
		class:arrival-hidden={arrivingAtModels}
		data-plate={plate}
		aria-hidden={pastHero || arrivingAtModels || undefined}
		inert={pastHero || arrivingAtModels}
		bind:clientHeight={headerHeight}
		onfocusin={onHeaderFocusIn}
		onfocusout={onHeaderFocusOut}
	>
		{@render masthead('hero-models-tab', heroRefs)}
	</header>

	<!-- The fixed header waits behind the hero copy, then takes over with its own transition. -->
	<header
		class="plate"
		class:neutral-page={!plate}
		class:hidden={(!pastHero && !arrivingAtModels) || hidden}
		class:detached={pastHero && scrollY > 0}
		data-plate={plate}
		aria-hidden={!pastHero && !arrivingAtModels ? true : undefined}
		inert={!pastHero && !arrivingAtModels}
		bind:clientHeight={headerHeight}
		onfocusin={onHeaderFocusIn}
		onfocusout={onHeaderFocusOut}
	>
		{@render masthead('models-tab', headerRefs)}
	</header>
{:else}
	<header
		class="plate"
		class:neutral-page={!plate}
		class:hidden={hidden}
		class:detached={scrollY > 0}
		data-plate={plate}
		bind:clientHeight={headerHeight}
		onfocusin={onHeaderFocusIn}
		onfocusout={onHeaderFocusOut}
	>
		{@render masthead('models-tab', headerRefs)}
	</header>
{/if}

<!-- tabindex, so the skip link above moves focus here and not only the scroll. -->
<main id="content" class:neutral-page={!plate} tabindex="-1" data-plate={plate}>
	{@render children()}
</main>

<footer>
	<div class="page notes small muted">
		<p>Predictions are a model's estimate, published for information. This is not betting advice.</p>
		<p>This site is not affiliated with, endorsed by, or sponsored by the National Basketball Association.</p>

		{#if collectedThrough}
			<p>Built from games played through {collectedThrough}.</p>
		{:else}
			<p>The prediction service is not answering.</p>
		{/if}

		<ul class="links">
			<li><a class="text-link" href="/about">About</a></li>
			<li><a class="text-link" href="/terms-and-conditions">Terms and conditions</a></li>

			{#if ADS_ENABLED} 
				<li><a class="text-link" href="/privacy">Privacy</a></li>
			{/if}
		</ul>
	</div>
</footer>

<style>
	/*
	 * Printed on the band under it rather than set above it, so the top of every page is one object
	 * and the wordmark lines up with the work below it.
	 *
	 * It takes the current plane's inks through the .plate class in app.css, so every tab, rule and
	 * accent in the markup is already correct without a rule per element.
	 */
	header {
		position: fixed;
		z-index: var(--layer-header);
		inset: 0 0 auto;
		transition:
			translate var(--motion) var(--ease-in),
			background var(--motion-fast) var(--ease-in),
			box-shadow var(--motion-fast) var(--ease-in);
	}

	/* At rest it is part of the band it is printed on, so it has no ground of its own. */
	header.plate {
		background: transparent;
	}

	/* Neutral pages have no family stock. Their fixed header is block paper from the first pixel onward. */
	header.plate.neutral-page:not(.home-header) {
		background: var(--block);
	}

	/* The home header is a hero-owned copy of the shared masthead. It shares the hero's scroll
	   timeline, then leaves it at the Models section and returns to the normal fixed-header rules. */
	header.home-header {
		position: fixed;
	}

	/* A cross-page arrival at Models bypasses the hero, so its copy never flashes before the fixed
	   header takes over. */
	header.arrival-hidden {
		visibility: hidden;
	}

	@supports (animation-timeline: scroll()) {
		@media (prefers-reduced-motion: no-preference) {
			header.home-header {
				animation: hero-recede linear both;
				animation-timeline: scroll(root);
				animation-range: 0 100dvh;
			}
		}
	}

	/* Off the band and over the page, where it is a strip of plate in its own right. With no ground
	   and no shadow it reads as something cut out of the page rather than as something above it. */
	header.plate.detached {
		background: var(--plate);
		box-shadow: var(--shadow);
	}

	header.hidden {
		translate: 0 -100%;
		transition-timing-function: var(--ease-out);
	}

	/* Off screen until it is focused, then a printed slip in the top corner. */
	.skip {
		position: fixed;
		z-index: var(--layer-skip);
		top: var(--space-2);
		left: var(--space-4);
		translate: 0 -200%;
		background: var(--plate-spot);
		color: var(--plate-spot-on);
		transition: translate var(--motion) var(--ease-in);
	}

	.skip:focus-visible {
		translate: 0 0;
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
		color: var(--ink);
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
		color: var(--ink-muted);
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
		background: var(--hairline);
		border-radius: var(--radius);
	}

	/* Centred on the Models tab, and moved left by whatever centring would have hung past the page
	   gutter. It floats over the page, so it carries the shadow. */
	.menu > ul {
		position: absolute;
		z-index: var(--layer-floating);
		top: 100%;
		left: 50%;
		translate: calc(-50% - var(--menu-nudge, 0px)) 0;
		visibility: hidden;
		opacity: 0;
		width: max-content;
		max-width: min(24rem, calc(100vw - var(--space-5) * 2));
		margin-block-start: var(--space-2);
		padding: var(--space-2);
		background: var(--plate-deep);
		border: var(--rule-plate-strong);
		list-style: none;
		box-shadow: var(--shadow);
		transition:
			opacity var(--motion) var(--ease-in),
			visibility var(--motion);
	}

	.menu > ul a {
		display: flex;
		flex-direction: column;
		gap: 2px;
		justify-content: center;
		min-height: var(--tap-target);
		padding: var(--space-2) var(--control-padding-x);
		color: var(--plate-ink);
		text-decoration: none;
	}

	.entry-title {
		font-weight: 600;
	}

	.entry-note {
		color: var(--plate-ink-muted);
	}

	.menu > ul a:hover,
	.menu > ul a:focus-visible {
		background: var(--plate);
	}

	.menu > ul a:hover .entry-title,
	.menu > ul a:focus-visible .entry-title {
		color: var(--plate-spot);
	}

	/* The entry for the page the reader is already on. It leads nowhere, so it is marked with a rule
	   down its leading edge rather than underlined, which is what a link to somewhere else looks
	   like. */
	.menu > ul a[aria-current] {
		border-left: var(--rule-accent);
		border-left-color: var(--plate-spot);
		background: var(--plate);
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
	   when it hides. The band a page opens with takes that reservation back, in app.css, because the
	   header is printed on the band rather than set above it. */
	main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		padding-block: var(--header-height) var(--space-8);
	}

	/* It is only focusable so the skip link can land on it, so it never draws a ring of its own. */
	main:focus {
		outline: none;
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

	@media (min-width: 40rem) {
		.masthead {
			gap: var(--space-5);
		}

		.tabs {
			gap: var(--space-3);
		}
	}
</style>
