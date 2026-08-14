from fastapi import HTTPException

from nba_ml.api.app import all_models, family_about_models

import pytest


def test_model_about_copy_only_arrives_on_the_family_endpoint():
    catalogue = [model.model_dump() for model in all_models()]
    about_models = [model.model_dump() for model in family_about_models("player_stats")]

    assert all("title" not in model and "description" not in model for model in catalogue)
    assert all({"name", "title", "description", "published"} == model.keys() for model in about_models)
    assert len(about_models) == 14


def test_unknown_model_family_has_no_about_catalogue():
    with pytest.raises(HTTPException, match="No model family is named unknown") as raised:
        family_about_models("unknown")

    assert raised.value.status_code == 404
