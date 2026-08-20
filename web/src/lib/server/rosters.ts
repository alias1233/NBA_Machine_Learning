/**
 * Reading a roster out of a page's address bar, on the server.
 *
 * A URL that does not name the reader's own roster is answered with the one the chosen game
 * expects, so a link with nothing but a game in it still predicts the lineup that will take the
 * floor. Once the reader has pressed the button the URL says so, and from then on it is read
 * exactly as it stands, empty fields included. See `ROSTER_PARAMETER` in `$lib/rosters`.
 *
 * The ids in the URL are named back into players, so a shared link opens with its pills already
 * drawn rather than with a row of numbers. A name that cannot be resolved is dropped rather than
 * failing the page, because a link outliving a player is not a reason to show nothing.
 */

import { expectedOf, isReadersRoster, joinedParameter, outParameter, rosterOf } from '$lib/rosters';
import { getPlayer } from '$lib/server/api';

import type { RosterSide } from '$lib/rosters';
import type { Player, Roster, ScheduledGame, Scenario } from '$lib/types';

/** One side's roster change, as players, which is what the roster controls draw. */
export type NamedScenario = {
	out: Player[];
	joined: Player[];
};

/** Both sides of a game, which is what a team or game prediction names. */
export type GameScenarios = {
	home: NamedScenario;
	away: NamedScenario;
};

const EMPTY: NamedScenario = { out: [], joined: [] };

const readIds = (parameters: URLSearchParams, name: string) =>
	parameters
		.getAll(name)
		.map(Number)
		.filter((id) => Number.isInteger(id) && id > 0);

async function namePlayers(ids: number[]): Promise<Player[]> {
	const found = await Promise.all(ids.map((id) => getPlayer(id).catch(() => null)));

	return found.filter((player): player is Player => player !== null);
}

/**
 * What one side's roster parameters name, or what its game expects where they name nothing.
 *
 * A page about one team leaves the side off.
 */
export async function readScenario(
	parameters: URLSearchParams,
	expected: NamedScenario,
	side?: RosterSide
): Promise<NamedScenario> {
	if (!isReadersRoster(parameters)) return expected;

	const [out, joined] = await Promise.all([
		namePlayers(readIds(parameters, outParameter(side))),
		namePlayers(readIds(parameters, joinedParameter(side)))
	]);

	return { out, joined };
}

/** The lineup change each side of a chosen game expects, which is what a page opens on. */
export function expectedScenarios(rosters: Roster[], game: ScheduledGame | null): GameScenarios {
	if (game === null) return { home: EMPTY, away: EMPTY };

	return {
		home: expectedOf(rosterOf(rosters, game.home_team.abbreviation)),
		away: expectedOf(rosterOf(rosters, game.away_team.abbreviation))
	};
}

/** Both sides at once, which is what a team or game prediction names. */
export async function readGameScenarios(
	parameters: URLSearchParams,
	expected: GameScenarios
): Promise<GameScenarios> {
	const [home, away] = await Promise.all([
		readScenario(parameters, expected.home, 'home'),
		readScenario(parameters, expected.away, 'away')
	]);

	return { home, away };
}

/** The same change written the way the prediction service asks for one. */
export const scenarioRequest = ({ out, joined }: NamedScenario): Scenario => ({
	without: out.map(({ id }) => id),
	returning: joined.map(({ id }) => id)
});

const samePlayers = (chosen: Player[], expected: Player[]) =>
	chosen.length === expected.length &&
	chosen.every((player) => expected.some(({ id }) => id === player.id));

/**
 * Whether the reader moved away from the lineup the page suggested.
 *
 * This is what an answer says beside its figure, so it must not fire for the expected lineup
 * itself. A prediction made for whoever will actually play is the ordinary one, not a what-if.
 */
export const isChanged = (chosen: NamedScenario, expected: NamedScenario) =>
	!samePlayers(chosen.out, expected.out) || !samePlayers(chosen.joined, expected.joined);

/** The same, over both sides of a game. */
export const isGameChanged = (chosen: GameScenarios, expected: GameScenarios) =>
	isChanged(chosen.home, expected.home) || isChanged(chosen.away, expected.away);
