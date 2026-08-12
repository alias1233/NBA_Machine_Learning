"""
Building the whole league's features once, so that a prediction does not build them for itself.

This is the job behind the prediction service. It reads the stored box scores, builds every column
any player game statistics model reads, and publishes the result. The service picks the new build up
without a restart and keeps the previous one until this succeeds again.

Every choice is a command line argument and nothing is asked for at a prompt, so the command a person
runs by hand is the command a scheduled job runs. Collect first, because a build only holds what is
stored.
"""

import argparse

from dateutil.relativedelta import relativedelta

from nba_ml import season
from nba_ml.feature_engineering import feature_store
from nba_ml.models.player_stats import features, specifications

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

    print_debug = not arguments.quiet
    window_start_date = (
        None if arguments.everything_stored
        else season.today() - relativedelta(years=arguments.window_years)
    )

    feature_set = specifications.union_feature_set()
    histories = features.build_league_histories(feature_set, window_start_date, print_debug)
    build = feature_store.from_histories(histories, feature_set.sequence_columns, window_start_date)
    written_to = feature_store.publish(features.BUILD_NAME, build)

    print(
        f"Published {build.game_count} games of {len(build.subjects)} players over "
        f"{len(build.sequence_columns)} columns to {written_to}."
    )

if __name__ == "__main__":
    main()
