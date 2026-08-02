def _build_path(base_directory: str, name: str, category: str | None) -> str:
    if category is not None:
        base_directory += category + "/"

    return base_directory + name

SAVE_MODELS_DIRECTORY_PATH = "trained_models/"
MODEL_FILE_ENDING = "/model.pth"
def get_model_save_path(name: str, category: str | None) -> str:
    return _build_path(SAVE_MODELS_DIRECTORY_PATH, name, category) + MODEL_FILE_ENDING

TRAINING_REPORT_FILE_ENDING = "/training_report.txt"
def get_model_save_training_report_path(name: str, category: str | None) -> str:
    return _build_path(SAVE_MODELS_DIRECTORY_PATH, name, category) + TRAINING_REPORT_FILE_ENDING

SAVE_PROCESSED_TRAINING_DATA_PATH = "training_data_preprocessed/"
TRAINING_DATA_ENDING = "/training_data.pth"
def get_model_save_training_data_path(name: str, category: str | None) -> str:
    return _build_path(SAVE_PROCESSED_TRAINING_DATA_PATH, name, category) + TRAINING_DATA_ENDING

SAVE_GRAPHS_DIRECTORY_PATH = "graphs/"
def get_model_save_graphs_directory_path(name: str, category: str | None) -> str:
    return _build_path(SAVE_GRAPHS_DIRECTORY_PATH, name, category)
