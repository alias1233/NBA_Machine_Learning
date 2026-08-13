"""
Turning stored box scores into columns a model can read.

One named column at a time is built by game_columns.py and the four modules grouped by what they
describe: player_columns.py, team_columns.py, schedule_columns.py and season_columns.py. rolling.py
builds windows over a column, and samples.py cuts a finished frame into the samples a model is fit
on. None of them decides which columns a model wants, which is a model family's own business.
"""
