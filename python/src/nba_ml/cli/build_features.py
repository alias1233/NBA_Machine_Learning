"""Command for building the player feature cache."""

import argparse

from dateutil.relativedelta import relativedelta

from nba_ml import season
from nba_ml.feature_engineering import feature_store
from nba_ml.models.player_stats import features, specifications


def build(
    window_years: int = features.HISTORICAL_WINDOW_LENGTH_YEARS,
    everything_stored: bool = False,
    print_debug: bool = True
    ):
    """Builds and publishes the feature cache used by the prediction service."""

    window_start_date = (
        None if everything_stored
        else season.today() - relativedelta(years=window_years)
    )
    feature_set = specifications.union_feature_set()
    histories = features.build_league_histories(feature_set, window_start_date, print_debug)
    feature_build = feature_store.from_histories(histories, feature_set.sequence_columns, window_start_date)
    written_to = feature_store.publish(features.BUILD_NAME, feature_build)
    print(
        f"Published {feature_build.game_count} games of {len(feature_build.subjects)} players over "
        f"{len(feature_build.sequence_columns)} columns to {written_to}."
    )
    return written_to

def main():
    parser = argparse.ArgumentParser(
        description="Builds the whole league's features and publishes them for the service to read."
    )
    parser.add_argument(
        "--window-years",
        type=int,
        default=features.HISTORICAL_WINDOW_LENGTH_YEARS,
        metavar="YEARS",
        help="How far back to build. Every window the columns read fits inside the default."
    )
    parser.add_argument(
        "--everything-stored",
        action="store_true",
        help="Build every game held rather than a window. Peaks above what the server has."
    )
    parser.add_argument("--quiet", action="store_true", help="Only print where the build was written.")
    arguments = parser.parse_args()

    build(arguments.window_years, arguments.everything_stored, not arguments.quiet)

if __name__ == "__main__":
    main()
