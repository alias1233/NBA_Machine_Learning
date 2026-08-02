import torch
from pathlib import Path
from typing import Iterable, Sized

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
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, path)

# Logging helpers

def print_datasets(
    datasets: Iterable[Sized],
    num_to_print: int = 5,
    print_values: bool = True,
    print_summary: bool = True
    ):
    """
    Prints the first few entries and the length of each dataset.
    """

    for dataset in datasets:
        if print_summary:
            print(f"Number of data chunks: {len(dataset)}")

        if not print_values:
            continue

        for index, data in enumerate(dataset):
            if index >= num_to_print:
                break

            print(data)

def print_labeled_dataset(
    labeled_datasets: tuple,
    num_to_print: int = 5,
    print_values: bool = True,
    print_summary: bool = True
    ):
    """
    Prints the column names, and optionally the first few entries, of labeled input and output data.

    Args:
        labeled_datasets must start with (input chunks, output chunks). Each input chunk is a
        dict of dataframes, and each output chunk is a dataframe.
    """

    input_data, output_data = labeled_datasets[0], labeled_datasets[1]

    if not input_data or not output_data:
        print("No labeled data to print.")
        return

    if print_summary:
        print('-----------------------------------------------------')

        for label, dataframe in input_data[0].items():
            print(f'Input- | Label: {label} | Columns: ')
            for column_name in dataframe.columns:
                print(column_name)

        print('-----------------------------------------------------')
        print('Output- | Columns: ')
        for column_name in output_data[0].columns:
            print(column_name)
        print('-----------------------------------------------------')

    if print_values:
        for input_chunk, output_chunk in list(zip(input_data, output_data))[:num_to_print]:
            print(input_chunk)
            print(output_chunk)

