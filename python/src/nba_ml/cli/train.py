"""
Training one player game statistics model.

Which model to fit is an argument, so adding a model to specifications.py is the only thing needed
to train it.
"""

import argparse

from nba_ml.models.player_stats import specifications, training

def main():
    parser = argparse.ArgumentParser(
        description="Trains one player game statistics model and saves it with a report of the run."
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=specifications.MODEL_NAMES,
        help="Which model to train, named as it is in specifications.py."
    )
    parser.add_argument(
        "--skip-evaluations",
        action="store_true",
        help="Train and save without scoring the finished model or writing graphs."
    )
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Ignore the saved preprocessed build and engineer the features again."
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Neither read nor write the preprocessed build, which is about a gigabyte per model."
    )
    parser.add_argument("--quiet", action="store_true", help="Only print what the training loop reports.")
    arguments = parser.parse_args()

    training.train(
        specifications.ALL_MODEL_SPECIFICATIONS[arguments.model],
        output_evaluations=not arguments.skip_evaluations,
        use_cached_build=not (arguments.rebuild_cache or arguments.no_cache),
        save_cached_build=not arguments.no_cache,
        print_debug=not arguments.quiet
    )

if __name__ == '__main__':
    main()
