"""
The game statistics models: what happens in a game, whichever side you look from.

A prediction here names a game and nothing else, so a game is one sample and the model reads both
teams' past games. A value that has a direction is read from the home team's row, which is what
makes a positive point differential the home team's margin.

features.py builds what the models read, specifications.py says what each model is, training.py fits
one, and inference.py runs a saved one. The rows underneath them are built in
feature_engineering/team_game_rows.py and shared with team statistics.
"""
