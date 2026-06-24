import requests
import time
from datetime import datetime

from nba_api.stats.static import teams, players
from nba_api.stats.library.parameters import Season, SeasonTypeAllStar

def get_oldest_season_with_all_player_box_score_data_data():
    return 1996

def get_current_nba_season():
    return Season.current_season_year

def convert_year_to_NBA_season(season_year: int) -> str:
    return str(season_year) + '-' + str(season_year + 1)[-2:]

NBA_DATE_FORMAT = "%Y-%m-%d"
def convert_datetime_to_str_nba_date_format(date: datetime) -> str:
    return date.strftime(NBA_DATE_FORMAT)

def convert_str_to_datetime_nba_date_format(date: str) -> datetime:
    return datetime.strptime(date, NBA_DATE_FORMAT)

def get_all_season_types() -> list[str]:
    return [SeasonTypeAllStar.preseason, SeasonTypeAllStar.regular, SeasonTypeAllStar.playin, SeasonTypeAllStar.playoffs]

def get_all_teams():
    return teams.get_teams()

def team_abb_to_id(abbreviation: str) -> str:
    team = teams.find_team_by_abbreviation(abbreviation)
    if team != None:
        return team["id"]
    raise ValueError(
        f"{abbreviation} does not correspond with a team."
    )

def team_name_to_id(name: str) -> str:
    team = teams.find_teams_by_full_name(name)
    if team == []:
        raise ValueError(
        f"{name} does not correspond with a team."
        )
    return team[0]['id']

def team_id_to_name(id: str) -> str | None:
    team_data = teams.find_team_name_by_id(id)
    if team_data is None:
        return None
    
    return team_data['full_name']

def get_all_players():
    """
    NOTE: This is not always updated.
    """

    return players.get_players()

def player_name_to_ids(name: str) -> list:
    players_data = players.find_players_by_full_name(name)
    ids = []
    for player in players_data:
        ids.append(player["id"])
    return ids

def player_id_to_name(id: str) -> str | None:
    player_data = players.find_player_by_id(id)
    if player_data is None:
        return None
    
    return player_data['full_name']

def retry(func, retries: int = 3, timeout: int = 5):
    """
    Wrapper to retry a function call [retries] times as originally defined in:
    https://github.com/swar/nba_api/blob/master/docs/examples/Home%20Team%20Win-Loss%20Modeling/Home%20Team%20Win-Loss%20Data%20Prep.ipynb
    """

    def retry_wrapper(*args, **kwargs):
        attempts = 0
        while attempts < retries:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                print(e)
                time.sleep(timeout)
                attempts += 1

    return retry_wrapper