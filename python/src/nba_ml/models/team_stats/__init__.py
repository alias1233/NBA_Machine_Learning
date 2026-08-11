"""
The team statistics models: what one named team does in a game.

A prediction here names a team, because the answer belongs to that side and would be a different
number for the other one. Both sides of a game are training samples, so the schedule gives this
family two samples per game.

features.py builds what the models read, specifications.py says what each model is, training.py fits
one, and inference.py runs a saved one. The rows underneath them are built in
feature_engineering/team_game_rows.py and shared with game statistics.
"""
