/**
 * The images of the hero collage, in the order the hero's grid places them.
 *
 * A tile shows one image in the shared treatment, so any picture drops in without being prepared
 * first. A null entry paints the placeholder across the exact cell a real one will take, so filling
 * it in shifts nothing.
 *
 * Four is the minimum and six is the ceiling. Six is what the entrance is timed against and what the
 * grid places, so a seventh needs both revisited.
 */

export const TILES: (string | null)[] = [
	'basketball_through_hoop.jpg',
	'bizzare_basketball.png',
	'basketball_on_floor.jpg',
	'dunk.jpg',
	'basketball_court.jpg',
	'basketball_court_artistic.jpg'
];
