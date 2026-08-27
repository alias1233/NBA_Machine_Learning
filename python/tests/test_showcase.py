"""
Which models the home page's daily draw may pick from.

The home page shows an answer nobody asked for, so it is the site showing what it can do. Two rules
decide what is in the draw: the model has to be able to answer at all, and its answer has to have
enough outcomes in it to be worth drawing. A yes or no model breaks the second one, and adding a
narrow model later should fail here rather than turn up on the home page.
"""

from nba_ml import showcase
from nba_ml.models.families import ALL_FAMILIES, ModelFamily

YES_OR_NO = {"double_double", "triple_double", "win_probability"}
"""Every model whose answer is two outcomes. They are predicted on request and never drawn."""

def _everything_published(family: ModelFamily) -> ModelFamily:
    """The same family with every model able to answer, since no model file is saved in a test."""

    return ModelFamily(family.name, family.specifications, lambda specification: True)

# WHAT IS WORTH DRAWING: #
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
