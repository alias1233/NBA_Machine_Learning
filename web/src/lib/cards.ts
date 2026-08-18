/**
 * A scheduled game dealt as a playing card.
 *
 * Which suit a game is printed with, and how far off square it lies on the board, both come from the
 * game's own id. So a card is the same card on the server and in the browser, on every render, and
 * for every reader, and nothing about the board moves when the page hydrates.
 *
 * None of it means anything. It is what makes a night of games read as a hand dealt on a board
 * rather than as a grid of identical tiles, and the facts a reader needs are printed on the card in
 * the two corner indices, exactly where a playing card prints its own.
 */

export type Suit = 'spade' | 'heart' | 'diamond' | 'club';

/**
 * The four suits, drawn rather than typed.
 *
 * Each is a filled path on a 24 by 24 box, so one holds at a corner index and at watermark size
 * without a second asset and without a font that has to be loaded to show a shape.
 */
export const SUIT_PATH: Record<Suit, string> = {
	spade:
		'M12 2.7 20.1 10.8a5 5 0 0 1-7 7.1L12 16.8l-1.1 1.1a5 5 0 1 1-7-7.1Z' +
		'M12 15.5c.9 3.2 1.4 5.7 3 7.6h-6c1.6-1.9 2.1-4.4 3-7.6Z',
	heart: 'M12 21.3 3.9 13.2a5 5 0 0 1 7-7.1L12 7.2l1.1-1.1a5 5 0 1 1 7 7.1Z',
	diamond: 'M12 1.8 20.6 12 12 22.2 3.4 12Z',
	club:
		'M12 3.2a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z' +
		'M7.2 10.4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z' +
		'M16.8 10.4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z' +
		'M12 12.5c.9 3.4 1.4 6.4 3 8.5h-6c1.6-2.1 2.1-5.1 3-8.5Z'
};

const SUITS: Suit[] = ['spade', 'heart', 'diamond', 'club'];

/** Red suits print in the plate's spot ink, black ones in the ink that reads on top of it. */
export const isRed = (suit: Suit) => suit === 'heart' || suit === 'diamond';

/** FNV-1a, which spreads an id well enough for four buckets and a tilt and costs one pass. */
function hash(id: string): number {
	let value = 0x811c9dc5;

	for (let at = 0; at < id.length; at++) {
		value ^= id.charCodeAt(at);
		value = Math.imul(value, 0x01000193);
	}

	return value >>> 0;
}

/** How far a dealt card lies off square, in degrees either way. */
const TILT = 2.5;

/** How far the tilt is stepped, which is what stops a row reading as one alternating angle. */
const TILT_STEPS = 21;

export type Deal = {
	suit: Suit;
	/** Degrees, negative or positive, to be written straight into a rotation. */
	tilt: number;
};

export function deal(id: string | number): Deal {
	const value = hash(String(id));

	return {
		suit: SUITS[value % SUITS.length],
		tilt: (((value >>> 3) % TILT_STEPS) / (TILT_STEPS - 1)) * TILT * 2 - TILT
	};
}
