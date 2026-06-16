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
    256,
    128,
    128
]

LEARNING_RATE = 0.0005
EPOCHS = 150
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
    
def train(debug: bool = False):

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # Fetching and rearranging training data
    datasets = player_props_processor.get_all_player_props_input_output_training_data(
        validation_split_start_date = VALIDATION_START_DATE,
        test_split_start_date = TEST_START_DATE,
        flatten = True,
        chunk_step_size = CHUNK_STEP_SIZE,
        print_debug = True
    )
    
    if debug:
        helpers.print_datasets(datasets, 1, False, True)
 
    (input_train, output_train, 
     input_val, output_val, 
     input_test, output_test, 
     input_scaler, output_scaler
     ) = datasets
 
    if debug:
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

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

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

    mae = np.mean(np.abs(predictions - actuals), axis=0)
    rmse = np.sqrt(np.mean((predictions - actuals) ** 2, axis=0))

    print("\n===== TEST RESULTS =====")
    print(f"PTS MAE : {mae[0]:.3f}")
    print(f"REB MAE : {mae[1]:.3f}")
    print(f"AST MAE : {mae[2]:.3f}")

    print(f"PTS RMSE: {rmse[0]:.3f}")
    print(f"REB RMSE: {rmse[1]:.3f}")
    print(f"AST RMSE: {rmse[2]:.3f}")

    print("\n===== SAMPLE PREDICTIONS =====")

    sample_size = min(50, len(predictions))
    indices = np.random.choice(len(predictions), size=sample_size, replace=False)

    for idx in indices:
        pred_pts, pred_reb, pred_ast = predictions[idx]
        actual_pts, actual_reb, actual_ast = actuals[idx]

        print(
            f"Sample {idx}: "
            f"Pred ({pred_pts:.1f}, {pred_reb:.1f}, {pred_ast:.1f}) | "
            f"Actual ({actual_pts:.1f}, {actual_reb:.1f}, {actual_ast:.1f})"
        )