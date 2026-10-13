import type { ScheduledGame } from '$lib/types';

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

// The en-CA locale formats a date as YYYY-MM-DD.
const GAME_DAY = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' });

/** Returns today's date as YYYY-MM-DD in US Eastern time, which the schedule uses. */
export const gameDayNow = (at: number | Date = Date.now()) => GAME_DAY.format(at);

/** Parses a timestamp from the service into milliseconds. Treated as UTC if it has no time zone. */
export const utcMoment = (iso: string) =>
	Date.parse(/(?:Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`);

export const gameDay = (date: string) => DAY.format(new Date(`${date}T00:00:00`));

export const longGameDay = (date: string) => LONG_DAY.format(new Date(`${date}T00:00:00`));

export const tipoffTime = (game: ScheduledGame) =>
	game.tipoff ? TIME.format(utcMoment(game.tipoff)) : null;

export const fullGameDay = (date: string) => FULL_DAY.format(new Date(`${date}T00:00:00`));

export const gameWhenFull = (game: ScheduledGame) =>
	[fullGameDay(game.date), tipoffTime(game)].filter(Boolean).join(', ');

function dayAfter(date: string): string {
	const at = new Date(`${date}T00:00:00Z`);

	at.setUTCDate(at.getUTCDate() + 1);

	return at.toISOString().slice(0, 10);
}

export function gameDayLabel(date: string, at: number | Date = Date.now()): string {
	const today = gameDayNow(at);

	if (date === today) return 'Today';
	if (date === dayAfter(today)) return 'Tomorrow';

	return fullGameDay(date);
}

/** Games on one day, earliest tipoff first. */
export type SlateDay = { date: string; games: ScheduledGame[] };

/** Returns a game's tipoff time in milliseconds, or Infinity if it has none. */
const tipoffAt = ({ tipoff }: ScheduledGame): number => {
	const at = tipoff ? utcMoment(tipoff) : NaN;

	return Number.isNaN(at) ? Infinity : at;
};

/** Groups games by the day they are played, earliest day first. */
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

/** Returns the games whose team names or abbreviations contain every word in the search. */
export function gamesMatching(games: ScheduledGame[], search: string): ScheduledGame[] {
	const words = search.toLowerCase().split(/\s+/).filter(Boolean);

	if (words.length === 0) return games;

	return games.filter((game) => {
		const sides = [
			game.away_team.name,
			game.away_team.abbreviation,
			game.home_team.name,
			game.home_team.abbreviation
		]
			.join(' ')
			.toLowerCase();

		return words.every((word) => sides.includes(word));
	});
}
