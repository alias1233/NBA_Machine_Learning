"""Tests for which models can be used for the home page's sample predictions."""

from nba_ml import showcase
from nba_ml.models.families import ALL_FAMILIES, ModelFamily

YES_OR_NO = {"double_double", "triple_double", "win_probability"}
"""Models with only two output classes."""

def _everything_published(family: ModelFamily) -> ModelFamily:
    """Returns the family with every model treated as published, since tests have no model files."""

    return ModelFamily(family.name, family.specifications, lambda specification: True)

# MODEL SELECTION: #
def test_a_yes_or_no_model_is_never_drawn_on_the_home_page():
    for family in ALL_FAMILIES:
        drawn = {
            specification.name
            for specification in showcase._worth_drawing(_everything_published(family))
        }

        assert drawn == set(family.specifications) - YES_OR_NO

def test_a_model_that_cannot_answer_is_not_drawn_however_wide_it_is():
    for family in ALL_FAMILIES:
        nothing_saved = ModelFamily(family.name, family.specifications, lambda specification: False)

        assert showcase._worth_drawing(nothing_saved) == []
