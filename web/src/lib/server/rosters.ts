import { expectedOf, isReadersRoster, joinedParameter, outParameter, rosterOf } from '$lib/rosters';
import { getPlayer } from '$lib/server/api';

import type { RosterSide } from '$lib/rosters';
import type { Player, Roster, ScheduledGame, Scenario } from '$lib/types';

/** One team's lineup changes as players, which is what the roster controls show. */
export type NamedScenario = {
	out: Player[];
	joined: Player[];
};

/** Lineup changes for both teams, as used by team and game predictions. */
export type GameScenarios = {
	home: NamedScenario;
	away: NamedScenario;
};

const EMPTY: NamedScenario = { out: [], joined: [] };

const readIds = (parameters: URLSearchParams, name: string) =>
	parameters
		.getAll(name)
		.map(Number)
		.filter((id) => Number.isInteger(id) && id > 0)
		.slice(0, 15);

async function namePlayers(ids: number[]): Promise<Player[]> {
	const found = await Promise.all(ids.map((id) => getPlayer(id).catch(() => null)));

	return found.filter((player): player is Player => player !== null);
}

/** Gets one team's lineup changes from the query parameters. Returns the expected ones if the user has not set a roster. */
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

/** Returns the expected lineup changes for both teams, which a page starts with. */
export function expectedScenarios(rosters: Roster[], game: ScheduledGame | null): GameScenarios {
	if (game === null) return { home: EMPTY, away: EMPTY };

	return {
		home: expectedOf(rosterOf(rosters, game.home_team.abbreviation)),
		away: expectedOf(rosterOf(rosters, game.away_team.abbreviation))
	};
}

/** Gets the lineup changes for both teams from the query parameters. */
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

/** Converts lineup changes into the format the prediction service expects. */
export const scenarioRequest = ({ out, joined }: NamedScenario): Scenario => ({
	without: out.map(({ id }) => id),
	returning: joined.map(({ id }) => id)
});

const samePlayers = (chosen: Player[], expected: Player[]) =>
	chosen.length === expected.length &&
	chosen.every((player) => expected.some(({ id }) => id === player.id));

/** Returns true if the chosen lineup differs from the expected one. */
export const isChanged = (chosen: NamedScenario, expected: NamedScenario) =>
	!samePlayers(chosen.out, expected.out) || !samePlayers(chosen.joined, expected.joined);

/** Same check, for both teams in a game. */
export const isGameChanged = (chosen: GameScenarios, expected: GameScenarios) =>
	isChanged(chosen.home, expected.home) || isChanged(chosen.away, expected.away);
