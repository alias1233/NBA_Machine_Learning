<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import type { ListedModel } from '$lib/models';
	import type { Snippet } from 'svelte';

	type Props = {
		models: ListedModel[];
		/** Label for screen readers. */
		label: string;
		/** Auto-scroll speed, in pixels per second. */
		speed?: number;
		/** Scroll position, shared with the visual copy. */
		position?: number;
		/** True for a visual copy. It follows the interactive list and does not respond to input. */
		passive?: boolean;
		entry: Snippet<[ListedModel]>;
	};

	let {
		models,
		label,
		speed = 20,
		position = $bindable(0),
		passive = false,
		entry
	}: Props = $props();

	/** Milliseconds to wait after the user scrolls before auto-scroll resumes. */
	const REST = 2500;
	/** Milliseconds to pause at either end before scrolling back. */
	const TURN_PAUSE = 1600;

	let scroller = $state<HTMLElement>();
	let printed = $state<HTMLElement>();

	let content = $state(0);
	let room = $state(0);
	let held = $state(false);
	let seen = $state(false);

	/** Scroll position as a float, because scrollTop rounds to whole pixels. */
	let at = 0;
	/** Time of the user's last scroll. */
	let worked = 0;
	let direction = 1;
	let pausedUntil = 0;

	const overflows = $derived(content > room + 1);

	const moves = $derived(overflows && !prefersReducedMotion.current);

	$effect(() => {
		if (passive || !scroller || !printed) return;

		const measure = new ResizeObserver(() => {
			content = printed!.offsetHeight;
			room = scroller!.clientHeight;
		});

		measure.observe(scroller);
		measure.observe(printed);

		return () => measure.disconnect();
	});

	$effect(() => {
		if (!passive || !scroller) return;

		at = position;
		scroller.scrollTop = position;
	});

	$effect(() => {
		if (passive || !scroller) return;

		const watch = new IntersectionObserver(([seeing]) => (seen = seeing.isIntersecting));

		watch.observe(scroller);

		return () => watch.disconnect();
	});

	$effect(() => {
		const roller = scroller;

		if (passive || !moves || !seen || held || !roller) return;

		let frame = 0;
		let last = 0;

		at = roller.scrollTop;

		const creep = (now: number) => {
			frame = requestAnimationFrame(creep);

			// Caps the time step, because a tab returning from the background reports one huge gap.
			const since = last ? Math.min(now - last, 100) : 0;

			last = now;

			if (now - worked < REST || now < pausedUntil) return;

			const end = direction > 0 ? roller.scrollHeight - roller.clientHeight : 0;
			const next = at + direction * (speed * since) / 1000;

			if ((direction > 0 && next >= end) || (direction < 0 && next <= end)) {
				stand(end);
				direction *= -1;
				pausedUntil = now + TURN_PAUSE;
			} else {
				stand(next);
			}
		};

		frame = requestAnimationFrame(creep);

		return () => cancelAnimationFrame(frame);
	});

	function stand(to: number) {
		at = to;
		position = to;

		if (scroller) scroller.scrollTop = to;
	}

	function moved() {
		if (!scroller || passive) return;

		if (Math.abs(scroller.scrollTop - at) > 1) {
			at = scroller.scrollTop;
			position = at;
			worked = performance.now();
		}

	}

	/** Pauses auto-scroll while the pointer is over the list. Touch is skipped because it never sends a leave event. */
	function rest(on: boolean) {
		return (event: PointerEvent) => {
			if (!passive && event.pointerType !== 'touch') held = on;
		};
	}
</script>

<div class="stage" style:--reach="{content}px">
	<span class="ground" aria-hidden="true"></span>

	<!-- A scrollable region must be reachable by keyboard. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="roll"
		bind:this={scroller}
		role={overflows && !passive ? 'group' : undefined}
		aria-label={overflows && !passive ? `${label}, scrollable` : undefined}
		tabindex={overflows && !passive ? 0 : undefined}
		onscroll={moved}
		onpointerenter={rest(true)}
		onpointerleave={rest(false)}
		onfocusin={() => !passive && (held = true)}
		onfocusout={() => !passive && (held = false)}
		>
		<ol class="printed" bind:this={printed}>
			{#each models as model (model.name)}
				<li>{@render entry(model)}</li>
			{/each}
		</ol>
	</div>
</div>

<style>
	.stage {
		position: relative;
		min-height: 0;
	}

	.ground {
		position: absolute;
		inset: 0 0 auto;
		height: min(100%, var(--reach, 100%));
	}

	.roll {
		position: absolute;
		inset: 0;
		overflow-y: auto;
		overscroll-behavior: contain;
		/* Auto-scroll sets scrollTop every frame, so smooth scrolling must stay off. */
		scroll-behavior: auto;
		scrollbar-width: none;
	}

	.roll::-webkit-scrollbar {
		display: none;
	}

	.printed {
		margin: 0;
		padding: 0;
		list-style: none;
	}

</style>
