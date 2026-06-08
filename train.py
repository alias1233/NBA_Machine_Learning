from src.data_preparation.data_preprocessing import player_props_processing

if __name__ == '__main__':
    input_data, output_data = player_props_processing.get_over_under_input_output_data(True)

    import pandas as pd
    pd.set_option("display.max_rows", 10)
    pd.set_option("display.max_columns", 100)

    # print(input_data)
    print(output_data)