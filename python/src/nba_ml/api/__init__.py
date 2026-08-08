"""
The prediction service, run with `uvicorn nba_ml.api:app`.

It listens on the internal network only and is a thin layer over each family's inference module. It
holds no logic of its own.
"""

from nba_ml.api.app import app

__all__ = ["app"]
