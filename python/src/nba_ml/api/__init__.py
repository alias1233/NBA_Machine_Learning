"""Prediction API. Run it with `uvicorn nba_ml.api:app`."""

from nba_ml.api.app import app

__all__ = ["app"]
