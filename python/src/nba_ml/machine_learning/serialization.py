from pathlib import Path

import torch

def load_data_from_file(file_path: Path):
    # Read onto the processor whatever the file was written from. Training uses any accelerator it
    # finds and saves the tensors on it, so a file written on a graphics card cannot be read at all
    # on a processor-only server without this. Callers that want another device move the model there
    # themselves, which is what trainer.train and trainer.predict already do.
    #
    # weights_only stays off because a saved model file carries its scikit-learn scaler, which is
    # not plain tensors. That also means loading a file runs whatever is inside it, so save the
    # scaler as plain arrays and turn this back on before model files come from anywhere but here.
    return torch.load(file_path, map_location="cpu", weights_only=False)

def save_data_to_file(file_path: Path, save_data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, file_path)
