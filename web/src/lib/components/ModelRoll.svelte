<!--
	The models a family holds, printed as a roll that feeds past the reader.

	A family holds more models than a sheet has room for, and the whole family is what a reader is
	choosing between, so the index feeds rather than standing a part of it. Left alone it creeps
	upward on its own, slowly enough to read off. A reader resting on it, working it by hand or
	focusing into it stops it where it is, and it picks up again a few seconds after they let go.

	It is a real scroll region, so a wheel, a finger, a scrollbar and the arrow keys all work on it,
	and nobody is ever waiting on the creep to reach a model they can already see.

	The roll reaches each end, rests, then returns. It never repeats a model just to keep moving, so
	the count above it stays an honest picture of how much the family holds. Where the whole family
	fits, or where the reader asked for no motion, it stands still.
-->
<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import type { ListedModel } from '$lib/models';
	import type { Snippet } from 'svelte';

	type Props = {
		models: ListedModel[];
		/** What the roll is called to a reader who cannot see it, which is the family it belongs to. */
		label: string;
		/** How fast the roll creeps, in pixels a second. */
		speed?: number;
		/** The position shared with the visual copy used by the family frame's fill transition. */
		position?: number;
		/** A visual copy follows the interactive roll but never starts a second interaction. */
		passive?: boolean;
		/** How one model prints. The roll owns the feeding and the sheet owns the printing. */
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

	/** How long after the reader last moved the roll themselves before it picks up again. */
	const REST = 2500;
	/** How long the roll rests at either end before it returns. */
	const TURN_PAUSE = 1600;

	let scroller = $state<HTMLElement>();
	let printed = $state<HTMLElement>();

	/** The height of the one, complete family list. */
	let content = $state(0);
	/** What the scroller has room for. */
	let room = $state(0);
	/** Whether the reader is resting on the roll, which holds it where it is. */
	let held = $state(false);
	/** Whether the roll is in front of the reader at all. */
	let seen = $state(false);

	/**
	 * Where the roll stands, to the fraction of a pixel.
	 *
	 * A creep this slow moves a third of a pixel a frame, and the browser rounds what it reports a
	 * scroll position to be, so adding that third to what the element says its position is throws the
	 * fraction away every frame and the roll never moves at all. The roll keeps its own count and
	 * writes that, and reads the element only to notice a hand on it.
	 */
	let at = 0;
	/** When the reader last moved the roll themselves. Read inside the frame, so it is not tracked. */
	let worked = 0;
	/** Which end the roll is traveling toward. It survives a reader briefly resting on it. */
	let direction = 1;
	/** The moment the roll may leave the end it just reached. */
	let pausedUntil = 0;

	/** More models than there is room for, so the reader has to be able to move it themselves. */
	const overflows = $derived(content > room + 1);

	/** A reader who asked for no motion is given the same roll standing still. */
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

	// The contrast layer is visual only. It follows the one real roll so its words remain on the
	// same line while the frame's fill passes over them.
	$effect(() => {
		if (!passive || !scroller) return;

		at = position;
		scroller.scrollTop = position;
	});

	// Nothing feeds while the section is off the screen, which is most of the time a reader is here.
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

			// A tab coming back from the background hands over one enormous gap. Capping it keeps the
			// roll from jumping a screenful the moment the reader returns to it.
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

	/**
	 * A hand on the roll, whatever moved it: a wheel, a finger, a scrollbar or an arrow key.
	 *
	 * The creep writes what it has just worked out, so a position within a pixel of that is the roll's
	 * own and anything further away is the reader's.
	 */
	function moved() {
		if (!scroller || passive) return;

		if (Math.abs(scroller.scrollTop - at) > 1) {
			at = scroller.scrollTop;
			position = at;
			worked = performance.now();
		}

	}

	/**
	 * A finger is not a pointer resting on the sheet. It arrives, and it never leaves, so holding the
	 * roll on it would stop the roll for the rest of the visit. A touch moves the roll instead, and
	 * moving it is what rests it.
	 */
	function rest(on: boolean) {
		return (event: PointerEvent) => {
			if (!passive && event.pointerType !== 'touch') held = on;
		};
	}
</script>

<!-- The roll is laid out by the sheet and never the other way round, so what it holds takes no part
     in how tall the sheet is. Everything printed on it stands inside this box. -->
<div class="stage" style:--reach="{content}px">
	<span class="ground" aria-hidden="true"></span>

	<!-- A region the reader can scroll has to be reachable by keyboard, whether or not it is a
	     control. It takes a tab stop only while there is something in it to scroll to. -->
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
	/*
	 * The roll takes whatever the sheet has left between what the family is and the ways into it, and
	 * it clips rather than growing, because the sheet is what has to fit the screen.
	 *
	 * That is what the stage is for. A family is taller than any sheet, so a roll standing in the flow
	 * would set the height of the sheet, of the board, and of a section that is meant to be one
	 * screen. The stage takes the room the sheet gives it and the roll fills exactly that.
	 */
	.stage {
		position: relative;
		min-height: 0;
	}

	/*
	 * The ground the roll runs on, drawn as tall as the family needs and never taller. It is a box of
	 * its own rather than the stage's own background, because the stage takes the room the sheet gives
	 * it and a ground standing open under a family that has run out reads as a hole cut for nothing.
	 * It is laid before the roll, so it is under it without either of them naming a layer.
	 */
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
		/* The creep writes this every frame, so it must never be smoothed. */
		scroll-behavior: auto;
		/* The motion is what says the roll feeds, and a bar beside printed matter is not printed. */
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
