/**
 * The one screen the site treats as a phone.
 *
 * A phone reads the page as a single column and keeps no room for the header, because the header
 * puts itself away as soon as the reader scrolls down. Anything that walks the page or reaches for
 * room has to know which of the two it is on, and `app.css` sets the same width in CSS, so the two
 * cannot drift apart.
 *
 * The fallback is false, because a server rendering the page has no screen and the wide layout is
 * what the markup already assumes.
 */

import { MediaQuery } from 'svelte/reactivity';

export const phone = new MediaQuery('width < 40rem', false);

/**
 * Room to print a full batch of a family's models on the home page's index.
 *
 * The index is held to one screen on a landscape device and a reader has to reach the way into every
 * family without scrolling, so how many entries a sheet may print is a question about the screen's
 * height. Portrait always has the room, because there the listing scrolls rather than being held to
 * a screen. It cannot be answered in `app.css`, because the answer is a count of things rather than
 * a size.
 *
 * The fallback is true, because a server rendering the page has no screen and almost every device
 * has the room.
 */
export const roomForBatch = new MediaQuery('(orientation: portrait) or (height >= 53rem)', true);
