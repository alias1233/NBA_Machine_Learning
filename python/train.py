import argparse

from src.modules.model_managers.player_props import model_manager

def main():
    parser = argparse.ArgumentParser(description="Trains one player prop model and saves it with a report of the run.")
    parser.add_argument(
        "-stat",
        nargs="?",
        choices=sorted(model_manager.ALL_MODEL_SPECIFICATIONS),
        help="Which stat to predict."
    )
    parser.add_argument(
        "-arch", "--architecture",
        choices=[architecture.value for architecture in model_manager.Architecture],
        help="How the model reads a player's past games."
    )
    parser.add_argument(
        "-skip_eval", "--skip-evaluations",
        action="store_true",
        help="Train and save without scoring the test set or writing graphs."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print what the training loop reports."
    )
    arguments = parser.parse_args()

    if arguments.stat is None or arguments.architecture is None:
        print("Must supply the target stat and model architecture as a command line argument.")
        return

    model_manager.train(
        model_manager.ALL_MODEL_SPECIFICATIONS[arguments.stat],
        model_manager.Architecture(arguments.architecture),
        output_evaluations=not arguments.skip_evaluations,
        print_debug=not arguments.quiet
    )

if __name__ == '__main__':
    main()
