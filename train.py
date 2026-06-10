from src.data_preparation.data_preprocessing import player_props_processing

if __name__ == '__main__':
    input_data, output_data = player_props_processing.get_all_player_props_input_output_training_data(step_size=10,print_debug=True)

    import pandas as pd
    pd.set_option("display.max_rows", 5)
    pd.set_option("display.max_columns", 100)

    for index, data in enumerate(input_data):
        print(data)

        if index >= 10:
            break

    for index, data in enumerate(output_data):
        print(data)

        if index >= 100:
            break