SAVE_MODELS_DIRECTORY_PATH = "trained_models/"
MODEL_FILE_ENDING = "/model.pth"
def get_model_save_path(name: str, category: str | None) -> str:
    path = SAVE_MODELS_DIRECTORY_PATH
    if category is not None:
        path += category + "/"
    return path + name + MODEL_FILE_ENDING

SAVE_PROCESSED_TRAINING_DATA_PATH = "training_data_preprocessed/"
TRAINING_DATA_ENDING = "/training_data.pth"
def get_model_save_training_data_path(name: str, category: str | None) -> str:
    path = SAVE_PROCESSED_TRAINING_DATA_PATH
    if category is not None:
        path += category + "/"
    return path + name + TRAINING_DATA_ENDING

SAVE_GRAPHS_DIRECTORY_PATH = "graphs/"
def get_model_save_graphs_directory_path(name: str, category: str | None) -> str:
    path = SAVE_GRAPHS_DIRECTORY_PATH
    if category is not None:
        path += category + "/"
    return path + name