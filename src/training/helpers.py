import torch
from pathlib import Path
import pandas as pd

def get_best_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def load_data_from_file(file_path: str):
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
    directory_path = file_path.rpartition('/')[0]
    save_model_path = Path(directory_path)
    save_model_path.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, file_path)

# Logging helpers

# TODO: Refactor these
def print_datasets(datasets, num_to_print = 5, print_values = True, print_summary = True):
    for dataset in datasets:
        if print_values:
            try:
                for index, data in enumerate(dataset):
                    if index > num_to_print:
                        break

                    print(data)
            except:
                pass
        
        if print_summary:
            try:
                print(f"Number of data chunks: {len(dataset)}")
            except:
                pass

def print_labeled_dataset(labeled_datasets,  num_to_print = 5, print_values = True, print_summary = True):
    if print_summary:
        print('-----------------------------------------------------')

        # TODO: Support more types
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

    if print_values:
        input_training_data = labeled_datasets[0]
        output_training_data = labeled_datasets[1]

        for i, input_training_data_chunk in enumerate(input_training_data):
            if i >= num_to_print:
                break

            print(input_training_data_chunk)
            print(output_training_data[i])