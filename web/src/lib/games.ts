/**
 * Writing a scheduled game out for a reader, and reading the two ways it names when it is played.
 *
 * Dates cross the wire as YYYY-MM-DD and are the date the game is played on, so they are read as a
 * plain calendar day rather than a moment in time. A tip-off is a real moment and is sent in UTC.
 */

import type { ScheduledGame } from '$lib/types';

/*
 * Built once and reused. `toLocaleDateString` builds a formatter on every call, which measured 0.35ms
 * against 0.012ms for a reused one, and a list of games pays that per card. The reader's own locale
 * is read here rather than named, and it cannot change while the page is open.
 */
const DAY = new Intl.DateTimeFormat(undefined, {
	weekday: 'short',
	month: 'short',
	day: 'numeric'
});
const LONG_DAY = new Intl.DateTimeFormat(undefined, { dateStyle: 'long' });
const FULL_DAY = new Intl.DateTimeFormat(undefined, {
	weekday: 'long',
	month: 'long',
	day: 'numeric'
});
const TIME = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });

/*
 * A game is filed under its United States eastern date, which is the date its box score is written
 * under, so that is the day the site means by today whatever the reader's or the server's clock
 * says. `en-CA` is the one common locale that writes a date the way the wire does. The rule is the
 * same one `python/src/nba_ml/season.py` states, and the two have to agree or a set built this
 * morning reads as yesterday's for five hours.
 */
const GAME_DAY = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' });

/** Today, as the schedule counts days: YYYY-MM-DD in United States eastern time. */
export const gameDayNow = (at: number | Date = Date.now()) => GAME_DAY.format(at);

/**
 * A moment the service sent, as milliseconds, which is UTC whether or not it wrote the zone down.
 *
 * The same rule the collector reads a tip-off by, in `python/src/nba_ml/upcoming.py`. Left to the
 * browser, a moment with no zone on it is read as the reader's own, which moves a tip-off by
 * however far from UTC they happen to be. NaN where there is no moment to read.
 */
export const utcMoment = (iso: string) =>
	Date.parse(/(?:Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`);

export const gameDay = (date: string) => DAY.format(new Date(`${date}T00:00:00`));

export const longGameDay = (date: string) => LONG_DAY.format(new Date(`${date}T00:00:00`));

export const tipoffTime = (game: ScheduledGame) =>
	game.tipoff ? TIME.format(utcMoment(game.tipoff)) : null;

/** The day written out with its weekday, which is how the game a form is about names itself. */
export const fullGameDay = (date: string) => FULL_DAY.format(new Date(`${date}T00:00:00`));

/** The day and the tip-off written out in full, for the head above a prediction's parameters. */
export const gameWhenFull = (game: ScheduledGame) =>
	[fullGameDay(game.date), tipoffTime(game)].filter(Boolean).join(', ');

/** The calendar day after this one, counted on the calendar rather than on anybody's clock. */
function dayAfter(date: string): string {
	const at = new Date(`${date}T00:00:00Z`);

	at.setUTCDate(at.getUTCDate() + 1);

	return at.toISOString().slice(0, 10);
}

/**
 * What a day of the board calls itself.
 *
 * The two days a reader already has a word for are given that word, because a reader looking for
 * tonight's game is looking for tonight and not for the twenty-fourth. Every other day is written
 * out in full, which is the only thing that tells one Saturday from the next.
 */
export function gameDayLabel(date: string, at: number | Date = Date.now()): string {
	const today = gameDayNow(at);

	if (date === today) return 'Today';
	if (date === dayAfter(today)) return 'Tomorrow';

	return fullGameDay(date);
}

/** The games of one day of the board, earliest tip-off first. */
export type SlateDay = { date: string; games: ScheduledGame[] };

/** When a game tips off, and after everything that has a time where the schedule names none. */
const tipoffAt = ({ tipoff }: ScheduledGame): number => {
	const at = tipoff ? utcMoment(tipoff) : NaN;

	return Number.isNaN(at) ? Infinity : at;
};

/**
 * The board's games filed under the day each is played on, earliest day first.
 *
 * A reader hunting for a game knows its day before they know anything else about it, so the day is
 * what the board is divided by and what each division is labelled with. Within a day the games are
 * in the order they are played, which is the order a night is read in.
 */
export function slateDays(games: ScheduledGame[]): SlateDay[] {
	const days = new Map<string, ScheduledGame[]>();

	for (const game of games) {
		const dealt = days.get(game.date);

		if (dealt) dealt.push(game);
		else days.set(game.date, [game]);
	}

	return [...days]
		.sort(([one], [two]) => one.localeCompare(two))
		.map(([date, dealt]) => ({
			date,
			games: dealt.sort((one, two) => {
				const [first, second] = [tipoffAt(one), tipoffAt(two)];

				return first === second ? 0 : first - second;
			})
		}));
}
