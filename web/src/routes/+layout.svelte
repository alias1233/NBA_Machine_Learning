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

	let { children, data } = $props();

	const here = $derived(page.url.pathname);
	const home = $derived(here === '/');
	const onModels = $derived(here.startsWith('/models'));

	const plate = $derived(plateOf(here));

	const predictable = $derived(data.families.filter((family) => family.published));

	const collectedThrough = $derived(
		data.health?.newest_stored_game ? longGameDay(data.health.newest_stored_game) : null
	);

	let atModels = $state(false);

	$effect(() => {
		if (!home) {
			atModels = false;
			return;
		}

		const section = document.getElementById(MODELS_SECTION);
		if (!section) return;

		const spy = new IntersectionObserver(([entry]) => (atModels = entry.isIntersecting), {
			rootMargin: '-45% 0px'
		});

		spy.observe(section);

		return () => spy.disconnect();
	});

	const canHover = new MediaQuery('hover: hover', true);

	let overMenu = $state(false);
	let revealed = $state(false);

	function onMenuPointerLeave() {
		overMenu = false;
	}

	/** Clicking the menu link for the current page only closes the menu. */
	function onFamilyEntry(event: MouseEvent, path: string) {
		if (here !== path) return;

		event.preventDefault();
		revealed = false;
	}

	/** On touch screens, the first tap opens the menu and the second follows the link. */
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

	$effect(() => {
		if (!revealed) return;

		const closeOutside = (event: PointerEvent) => {
			if (!activeRefs.menuRoot?.contains(event.target as Node)) revealed = false;
		};

		document.addEventListener('pointerdown', closeOutside);

		return () => document.removeEventListener('pointerdown', closeOutside);
	});

	// Centers the menu under its tab and shifts it left if it would overflow the page gutter.
	$effect(() => {
		// Referenced so the effect reruns on resize and when the family list changes.
		viewportWidth;
		predictable.length;

		if (!activeRefs.masthead || !activeRefs.menuRoot || !activeRefs.menuList) return;

		const gutter = parseFloat(getComputedStyle(activeRefs.masthead).paddingRight);
		const edge = activeRefs.masthead.getBoundingClientRect().right - gutter;
		const center = activeRefs.menuRoot.getBoundingClientRect().left + activeRefs.menuRoot.offsetWidth / 2;

		menuNudge = Math.max(center + activeRefs.menuList.offsetWidth / 2 - edge, 0);
	});

	let scrollY = $state(0);
	let headerHeight = $state(0);
	let nearTop = $state(false);
	let holdingFocus = $state(false);
	let scrolledUp = $state(false);
	let revealZone = $state(0);
	let arrivingAtModels = $state(false);
	function syncPastHero() {
		const models = document.getElementById(MODELS_SECTION);

		pastHero = home && !!models && models.getBoundingClientRect().top <= 0;
	}

	const hidden = $derived(
		holdingFocus
			? false
			: scrollY > headerHeight / 2 && !nearTop && !scrolledUp && !overMenu && !revealed
	);

	/** Scroll changes smaller than this many pixels are ignored. */
	const SCROLL_STEP = 8;

	let lastScroll = 0;

	function onScroll() {
		syncPastHero();

		const moved = window.scrollY - lastScroll;

		if (Math.abs(moved) < SCROLL_STEP) return;

		lastScroll = window.scrollY;

		if (moved > 0) {
			scrolledUp = false;
			revealed = false;
			return;
		}

		scrolledUp = !canHover.current;
	}

	// Ignores touch, because a touch leaves a stale pointer position behind.
	function onPointerMove(event: PointerEvent) {
		if (event.pointerType === 'touch') return;

		const near = event.clientY <= revealZone;

		if (near !== nearTop) nearTop = near;
	}

	// Only keyboard focus keeps the header open, because a click also focuses its target.
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

	afterNavigate(() => {
		document.documentElement.classList.remove('arriving');
		overMenu = false;
		holdingFocus = false;
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

<a class="skip button" href="#content">Skip to content</a>

{#snippet masthead(modelsTabId: string, refs: HeaderRefs, heroWordmark = false)}
	{@const ownsMenu = refs === activeRefs}
	<div class="page masthead" bind:this={refs.masthead}>
		<a
			class="wordmark"
			class:hero-wordmark={heroWordmark}
			class:wordmark-transition={heroWordmark ? !pastHero && !arrivingAtModels : !home}
			href="/"
		>
			{SITE_NAME}
		</a>

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
		{@render masthead('hero-models-tab', heroRefs, true)}
	</header>

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

<!-- tabindex lets the skip link move focus here, not only the scroll position. -->
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
			<li><a class="text-link" href="/privacy">Privacy</a></li>
		</ul>
	</div>
</footer>

<style>
	header {
		position: fixed;
		z-index: var(--layer-header);
		inset: 0 0 auto;
		transition:
			translate var(--motion) var(--ease-in),
			background var(--motion-fast) var(--ease-in),
			box-shadow var(--motion-fast) var(--ease-in);
	}

	header.plate {
		background: transparent;
	}

	header.plate.neutral-page:not(.home-header) {
		background: var(--block);
	}

	header.home-header {
		position: fixed;
	}

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

	header.plate.detached {
		background: var(--plate);
		box-shadow: var(--shadow);
	}

	header.hidden {
		translate: 0 -100%;
		transition-timing-function: var(--ease-out);
	}

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

	.wordmark-transition {
		view-transition-name: site-wordmark;
	}

	.hero-wordmark {
		font-size: clamp(1.125rem, 1rem + 0.9vw, 1.75rem);
		font-weight: 800;
		letter-spacing: 0.055em;
	}

	nav {
		flex: none;
	}

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

	.tabs > li > a[aria-current] {
		border-bottom-color: var(--plane-accent);
	}

	.menu {
		position: relative;
	}

	.menu.revealed > a {
		background: var(--hairline);
		border-radius: var(--radius);
	}

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

	.menu > ul a[aria-current] {
		border-left: var(--rule-accent);
		border-left-color: var(--plate-spot);
		background: var(--plate);
		cursor: default;
	}

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

	/* The fixed header is out of flow, so main adds padding for its height. */
	main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		padding-block: var(--header-height) var(--space-8);
	}

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

	@media (width < 24rem) {
		.masthead {
			gap: var(--space-2);
		}

		.tabs {
			gap: 0;
		}

		.tabs > li > a {
			justify-content: center;
			min-width: var(--tap-target);
			padding-inline: 0;
		}

		.hero-wordmark {
			font-size: 1.1rem;
		}
	}
</style>
