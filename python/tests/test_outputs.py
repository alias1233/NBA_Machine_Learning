"""Tests for the model output types."""

import numpy as np
import pytest

from nba_ml.machine_learning.datasets import _adjust_classification_outputs
from nba_ml.models.families import ALL_FAMILIES
from nba_ml.models.outputs import CategoryDistribution, IntegerDistribution, Values

# ONE CLASS PER INTEGER: #
def test_a_position_stands_for_one_whole_number():
    points = IntegerDistribution(minimum_value=0, outcomes=60)

    assert points.length == 60
    assert points.value_step == 1
    assert points.values(0) == [0]
    assert points.value_of(7) == 7
    assert points.label(7) == "7"

# BUCKETS: #
def test_a_bucket_covers_its_whole_width_and_is_read_as_its_middle():
    team_points = IntegerDistribution(minimum_value=80, outcomes=22, bucket_width=3)

    assert team_points.values(0) == [80, 81, 82]
    assert team_points.value_of(0) == 81
    assert team_points.label(0) == "80 to 82"
    assert team_points.values(21) == [143, 144, 145]

# IMPOSSIBLE VALUES: #
def test_an_impossible_value_comes_off_the_number_line_rather_than_out_of_a_bucket():
    differential = IntegerDistribution(
        minimum_value=-42,
        outcomes=28,
        bucket_width=3,
        impossible_value=0
    )

    below, above = differential.values(13), differential.values(14)

    assert below == [-3, -2, -1]
    assert above == [1, 2, 3]
    assert differential.label(13) == "-3 to -1"
    assert differential.value_of(14) == 2

    covered = [value for position in range(differential.length) for value in differential.values(position)]

    assert 0 not in covered
    assert len(covered) == differential.length * differential.bucket_width
    assert covered == sorted(covered)

def test_an_impossible_value_has_to_sit_on_a_bucket_edge():
    with pytest.raises(ValueError):
        IntegerDistribution(minimum_value=-42, outcomes=28, bucket_width=3, impossible_value=1)

    with pytest.raises(ValueError):
        IntegerDistribution(minimum_value=-42, outcomes=28, bucket_width=3, impossible_value=-42)

# VALUE TO CLASS CONVERSION: #
@pytest.mark.parametrize(
    "output",
    [
        IntegerDistribution(minimum_value=0, outcomes=60),
        IntegerDistribution(minimum_value=80, outcomes=22, bucket_width=3),
        IntegerDistribution(minimum_value=171, outcomes=35, bucket_width=3),
        IntegerDistribution(minimum_value=-42, outcomes=28, bucket_width=3, impossible_value=0)
    ]
)
def test_the_class_a_value_is_fit_against_is_the_position_it_is_read_back_out_of(output: IntegerDistribution):
    values = np.array([
        value
        for position in range(output.length)
        for value in output.values(position)
    ])
    classes = _adjust_classification_outputs(
        values,
        output.minimum_value,
        output.outcomes,
        output.bucket_width,
        output.impossible_value
    )

    expected = np.repeat(np.arange(output.length), output.bucket_width)

    assert np.array_equal(classes, expected)

def test_a_value_outside_the_range_folds_into_the_nearest_end():
    output = IntegerDistribution(minimum_value=80, outcomes=22, bucket_width=3)
    values = np.array([40, 79, 80, 145, 146, 200])

    classes = _adjust_classification_outputs(values, 80, 22, 3, None)

    assert list(classes) == [0, 0, 0, 21, 21, 21]
    assert output.values(0)[0] == 80

# OTHER OUTPUT TYPES: #
def test_a_category_answer_is_read_by_position_and_leads_with_the_first():
    win = CategoryDistribution(categories=("home win", "away win"))

    assert win.length == 2
    assert win.label(0) == "home win"
    assert win.first_value == 0
    assert win.value_step == 1
    assert win.impossible_value is None
    assert not win.ordered

def test_an_amount_answer_names_one_quantity_per_position():
    minutes = Values(quantities=("minutes",))

    assert minutes.length == 1
    assert minutes.label(0) == "minutes"

# ALL MODELS: #
def test_every_specification_agrees_with_its_own_output():
    specifications = [
        specification
        for family in ALL_FAMILIES
        for specification in family.specifications.values()
    ]
    names = [specification.name for specification in specifications]

    assert len(names) == len(set(names))
    assert specifications

    for specification in specifications:
        labels = [specification.output.label(position) for position in range(specification.output.length)]

        assert len(labels) == len(set(labels))
        assert specification.predicts
