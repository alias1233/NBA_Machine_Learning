/**
 * The images of the landing collage, in the order the placed grid of R8.4 lays them out.
 *
 * A tile shows one image, in the treatment section 8 describes, so any picture drops in without
 * being prepared first. A null entry paints the duotone placeholder across the exact cell a real
 * one will take, so filling it in shifts nothing.
 *
 * Four is the minimum and six is the ceiling. Six is what the entrance in R7.10 is timed against
 * and what the grid places, so a seventh needs both revisited. R8.3.
 */

export const TILES: (string | null)[] = [
	'basketball_through_hoop.jpg',
	"bizzare_basketball.png",
	"basketball_on_floor.jpg",
	"dunk.jpg",
	"basketball_court.jpg",
	"basketball_court_artistic.jpg"
];
