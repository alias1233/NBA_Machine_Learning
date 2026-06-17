from datetime import datetime
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler

from models import helpers
from . import player_props_processor
from src.training import trainer
from src.training.model_architectures import feed_forward
from src.training.model_architectures.feed_forward import FeedForward

SAVE_MODELS_DIRECTORY_PATH = 'trained_models/'

TEST_MODEL_DIRECTORY_PATH = SAVE_MODELS_DIRECTORY_PATH + 'player_prop/'
SAVE_TEST_MODEL_FILE_PATH = TEST_MODEL_DIRECTORY_PATH + 'model.pth'

RANDOM_SEED = 1

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

HIDDEN_LAYERS = [
    256,
    128,
    64
]

LEARNING_RATE = 0.0005
EPOCHS = 130
LOSS_FUNCTION = torch.nn.MSELoss()
LOG_LOSS_INTERVAL = 10

INPUT_SCALER = 'input_scaler'
OUTPUT_SCALER = 'output_scaler'

def load_model() -> tuple[torch.nn.Module, StandardScaler, StandardScaler]:
    full_model_params = torch.load(SAVE_TEST_MODEL_FILE_PATH, weights_only=False)
    model = FeedForward(
        full_model_params[feed_forward.INPUT_DIM],
        full_model_params[feed_forward.OUTPUT_DIM],
        full_model_params[feed_forward.HIDDEN_LAYERS]
    )
    model.load_state_dict(
        full_model_params[feed_forward.MODEL_STATE]
    )
    return (model, full_model_params[INPUT_SCALER], full_model_params[OUTPUT_SCALER])
    
def train(
        print_debug: bool = False,
        print_all_debug: bool = False
          ):
    
    if print_all_debug:
        import pandas as pd
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # Fetching and rearranging training data
    datasets = player_props_processor.get_all_player_props_input_output_training_data(
        validation_split_start_date = VALIDATION_START_DATE,
        test_split_start_date = TEST_START_DATE,
        flatten = True,
        chunk_step_size = CHUNK_STEP_SIZE,
        print_debug = print_debug,
        print_all_datasets = print_all_debug
    )
    
    helpers.print_datasets(datasets, 1, print_all_debug, print_debug)
 
    (input_train, output_train, 
     input_val, output_val, 
     input_test, output_test, 
     input_scaler, output_scaler
     ) = datasets
 
    if print_debug:
        print(f"Input feature dimensions: {input_train.shape}")
        print(f"Output feature dimensions: {output_train.shape}")

    in_features = input_train.shape[1]
    out_features = output_train.shape[1]

    # Creating model and training
    model = FeedForward(
        in_features,
        out_features,
        HIDDEN_LAYERS
    )

    optimizer = torch.optim.AdamW(
        model.parameters(), 
        lr=LEARNING_RATE
    )

    trainer.train(
        model,
        optimizer,
        EPOCHS,
        input_train,
        output_train,
        input_val,
        output_val,
        LOSS_FUNCTION,
        LOG_LOSS_INTERVAL
    )

    # Saving model data
    model_params = model.get_save_parameters_dict()
    scaler_params = {
        INPUT_SCALER : input_scaler,
        OUTPUT_SCALER : output_scaler
    }

    helpers.save_dictionary_data_to_file(SAVE_TEST_MODEL_FILE_PATH, [model_params, scaler_params])

    # Final evaluation on test data
    model, input_scaler, output_scaler = load_model()

    model.eval()
    with torch.no_grad():
        predictions_normalized: torch.Tensor = model(input_test).cpu()

    predictions = output_scaler.inverse_transform(predictions_normalized.numpy())
    actuals = output_scaler.inverse_transform(output_test.numpy())

    helpers.output_test_evaluation(
        predictions,
        actuals,
        output_size=15,
        labels=player_props_processor.OUTPUT_COLUMNS
    )