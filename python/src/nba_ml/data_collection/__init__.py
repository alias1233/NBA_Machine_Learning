"""
Filling the stores from a data source.

One module per kind of data. A collector decides what to ask for and writes down what comes back.
It never talks to a service itself, so the same collector works whatever the source is, and it
never waits for a person, so a scheduled job can run it.
"""
