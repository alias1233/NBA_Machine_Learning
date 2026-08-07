/**
 * The tiles of the landing collage.
 *
 * A tile shows one image, in the treatment section 8 describes, so any picture drops in without
 * being prepared first. A tile with no image yet paints a soft duotone shape and holds the exact box
 * a real one will take, so filling it in shifts nothing.
 *
 * Four is the minimum and six is the ceiling. Six is what the entrance in R7.7 is timed against, so
 * a seventh needs that timing recalculated.
 */

export type Tile = {
	/** A file under `static/collage/`, or null while the tile is a placeholder shape. */
	image: string | null;
	/** Which band the tile sits in. The words sit between the bands, so no tile can overlap them. */
	band: 'top' | 'bottom';
	/** Where it sits in its band, which is also the direction it drifts in from. */
	place: 'start' | 'centre' | 'end';
	/** Width against height, so a tile keeps its shape as its band gives up room. */
	ratio: number;
};

export const TILES: Tile[] = [
	{ image: 'basketball_through_hoop.jpg', band: 'top', place: 'start', ratio: 1.3 },
	{ image: null, band: 'top', place: 'centre', ratio: 0.9 },
	{ image: null, band: 'top', place: 'end', ratio: 1.6 },
	{ image: null, band: 'bottom', place: 'start', ratio: 1.5 },
	{ image: null, band: 'bottom', place: 'centre', ratio: 1.1 },
	{ image: null, band: 'bottom', place: 'end', ratio: 0.95 }
];
