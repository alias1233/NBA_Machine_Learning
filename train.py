from modules.model_managers.player_props import model_manager

if __name__ == '__main__':
    model_manager.train(model_manager.PLAYER_PROPS_POINTS_MODEL)
    # model_manager.train(model_manager.TEST_OVER_PARAMETERIZED_PLAYER_PROPS_POINTS_MODEL)