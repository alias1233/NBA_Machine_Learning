from datetime import datetime
import numpy as np
import torch, torch.nn as nn
from sklearn.preprocessing import StandardScaler

from . import data_processor
from src.data_preprocessing import training_data_processing
from src.training import trainer, helpers
from src.training.model_architectures import feed_forward
from src.training.model_architectures.feed_forward import FeedForward, LayerParameters
from src.training.loss_functions.gaussian_smoothed_cross_entropy_loss import GaussianSmoothedCrossEntropyLoss

SAVE_GRAPHS_DIRECTOR_PATH = "graphs/player_prop"

SAVE_MODELS_DIRECTORY_PATH = 'trained_models/'

TEST_MODEL_DIRECTORY_PATH = SAVE_MODELS_DIRECTORY_PATH + 'player_prop/'
SAVE_TEST_MODEL_FILE_PATH = TEST_MODEL_DIRECTORY_PATH + 'model.pth'

RANDOM_SEED = 5

TARGET_STAT = data_processor.TargetStat.PLAYER_POINTS
MINIMUM_OF_STAT = 0
NUM_STAT_CLASSIFICATIONS = 60

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

HIDDEN_LAYERS_PARAMETERS = [
    LayerParameters(256, nn.ReLU, True, 0.25),
    LayerParameters(256, nn.ReLU, True, 0.25),
    LayerParameters(256, nn.ReLU, True, 0.25),
    LayerParameters(256, nn.ReLU, True, 0.25)
]

LEARNING_RATE = 0.0005
EPOCHS = 100
LOSS_FUNCTION = GaussianSmoothedCrossEntropyLoss(NUM_STAT_CLASSIFICATIONS, 0.75)
EVALUATION_INTERVAL = 1
BATCH_SIZE = 512
PATIENCE = -1
MIN_DELTA = 0.001
DEVICE = helpers.get_best_device()
LOG_LOSS_INTERVAL = 1

INPUT_SCALER = 'input_scaler'

def load_model() -> tuple[torch.nn.Module, StandardScaler]:
    full_model_params = torch.load(SAVE_TEST_MODEL_FILE_PATH, weights_only=False)
    model = FeedForward(
        full_model_params[feed_forward.INPUT_DIM],
        full_model_params[feed_forward.OUTPUT_DIM],
        full_model_params[feed_forward.HIDDEN_LAYERS]
    )
    model.load_state_dict(
        full_model_params[feed_forward.MODEL_STATE]
    )
    return (model, full_model_params[INPUT_SCALER])
    
def train(
        print_debug: bool = True, 
        print_all_debug: bool = False
        ):
    
    if print_all_debug:
        import pandas as pd
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)    

    # Fetching and rearranging training data
    labeled_datasets = data_processor.get_all_player_props_input_output_labeled_data(
        TARGET_STAT,
        VALIDATION_START_DATE,
        TEST_START_DATE,
        CHUNK_STEP_SIZE,
        print_debug
    )

    # TODO: Move this print debugging somewhere else
    if print_debug:
        print('-----------------------------------------------------')
        input_training_data_chunk: dict[str, pd.DataFrame] = labeled_datasets[0][0]
        output_training_data_chunk: pd.DataFrame = labeled_datasets[1][0]
        for label, dataframe in input_training_data_chunk.items():
            print(f'Input- | Label: {label} | Columns: ')
            for column_name in list(dataframe.columns):
                print(column_name)

        print('-----------------------------------------------------')
        print(f'Output- | Columns: ')
        for column_name in list(output_training_data_chunk.columns):
            print(column_name)
        print('-----------------------------------------------------')

    if print_all_debug:
        print(labeled_datasets[0][0])
        print(labeled_datasets[1][0])

    datasets = training_data_processing.process_raw_data_for_classification_training(
        *labeled_datasets, 
        flatten=True,
        scale_input=True,
        min_output_value=MINIMUM_OF_STAT,
        num_classifications=NUM_STAT_CLASSIFICATIONS
        )
    
    helpers.print_datasets(datasets, 1, print_all_debug, print_debug)
 
    (input_train, output_train, 
     input_val, output_val, 
     input_test, output_test, 
     input_scaler
     ) = datasets
 
    if print_debug:
        print(f"Input feature dimensions: {str(input_train.shape)}")
        print(f"Output feature dimensions: {str(output_train.shape)}")

    in_features = input_train.shape[1]
    out_features = NUM_STAT_CLASSIFICATIONS

    # Creating model and training
    model = FeedForward(
        in_features,
        out_features,
        HIDDEN_LAYERS_PARAMETERS,
        True
    )

    optimizer = torch.optim.AdamW(
        model.parameters(), 
        lr=LEARNING_RATE
    )

    trainer.train(
        model,
        input_train,
        output_train,
        input_val,
        output_val,
        optimizer,
        loss_function=LOSS_FUNCTION,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        patience=PATIENCE,
        min_delta=MIN_DELTA,
        device=DEVICE,
        evaluation_interval=EVALUATION_INTERVAL,
        log_loss_interval=LOG_LOSS_INTERVAL
    )

    # Saving model data
    model_params = model.get_save_parameters_dict()
    scaler_params = {
        INPUT_SCALER : input_scaler
    }

    helpers.save_dictionary_data_to_file(SAVE_TEST_MODEL_FILE_PATH, [model_params, scaler_params])

    # Final evaluation on test data
    model, input_scaler = load_model()

    model.eval()
    with torch.no_grad():
        predictions_normalized: torch.Tensor = model(input_test).cpu()

    predictions = predictions_normalized.numpy()
    actuals = output_test.numpy()

    helpers.output_test_evaluation_classification(
        predictions,
        actuals,
        label=TARGET_STAT.value,
        output_size=20,
        save_graph_directory_path=SAVE_GRAPHS_DIRECTOR_PATH
    )