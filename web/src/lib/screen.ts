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
