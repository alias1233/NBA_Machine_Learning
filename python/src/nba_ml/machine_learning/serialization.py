from pathlib import Path

import torch

def load_data_from_file(file_path: Path):
    # Loads onto the CPU. weights_only is off because the file also contains scikit-learn scalers.
    return torch.load(file_path, map_location="cpu", weights_only=False)

def save_data_to_file(file_path: Path, save_data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, file_path)
