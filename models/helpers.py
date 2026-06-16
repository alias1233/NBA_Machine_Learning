import torch
from pathlib import Path

def save_dictionary_data_to_file(file_path: str, model_data: list[dict] | dict):
    directory_path = file_path.rpartition('/')[0]

    save_data = {}
    if isinstance(model_data, list):
        for dict in model_data:
            save_data.update(dict)

    else:
        save_data = model_data

    save_model_path = Path(directory_path)
    save_model_path.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, file_path)

def print_dataset(dataset, num_to_print):
    for index, data in enumerate(dataset):
        print(data)

        if index >= num_to_print:
            break

def print_datasets(datasets, num_to_print = 0, print_values = True, print_lengths = True):
    if print_values:
        import pandas as pd
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    for dataset in datasets:
        if print_values:
            try:
                print_dataset(dataset, num_to_print)
            except:
                pass
        
        if print_lengths:
            try:
                print(f"Number of data chunks: {len(dataset)}")
            except:
                pass