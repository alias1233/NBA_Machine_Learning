import torch
from pathlib import Path

def get_best_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def load_data_from_file(file_path: str):
    # weights_only stays off because a saved model file carries its scikit-learn scaler, which is
    # not plain tensors. That also means loading a file runs whatever is inside it, so save the
    # scaler as plain arrays and turn this back on before model files come from anywhere but here.
    return torch.load(file_path, weights_only=False)

def save_dictionary_data_to_file(file_path: str, model_data: list[dict] | dict):
    save_data = {}
    if isinstance(model_data, list):
        for d in model_data:
            save_data.update(d)

    else:
        save_data = model_data

    save_data_to_file(file_path, save_data)

def save_data_to_file(file_path: str, save_data):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, path)

