"""
The player game statistics models: how many points, rebounds or assists a player records in a game.

An answer is a probability for every whole number outcome, not a single number, so over and under
odds for any line are a sum over that array.

features.py builds what the models read, specifications.py says what each model is, training.py fits
one, inference.py runs a saved one, and odds.py reads the answer back.
"""
