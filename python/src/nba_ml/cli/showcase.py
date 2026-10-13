"""Command for building the home page's sample predictions."""

import argparse

from nba_ml import season, showcase

def main():
    parser = argparse.ArgumentParser(
        description="Builds the sample predictions the home page shows, and writes them where the service reads them."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=showcase.DEFAULT_COUNT,
        help=f"How many samples to draw. Default {showcase.DEFAULT_COUNT}."
    )
    parser.add_argument(
        "--day",
        type=season.from_date_string,
        default=None,
        help="The day to draw for, as YYYY-MM-DD. Defaults to today. The draw is seeded from it, so "
             "the same day always picks the same set."
    )
    arguments = parser.parse_args()

    day = None if arguments.day is None else arguments.day.date()
    built = showcase.build(arguments.count, day)
    written = showcase.write(built)

    print(f"Wrote {len(built.samples)} sample predictions for {built.built_for} to {written}.")

    if not built.samples:
        print(
            "Nothing was drawn. That is what no published model, or no upcoming game whose inputs "
            "are all collected, looks like."
        )

if __name__ == "__main__":
    main()
