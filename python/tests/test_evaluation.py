import numpy as np
import pytest

from nba_ml.machine_learning import evaluation


def test_interval_calibration_error_uses_the_probability_the_discrete_bounds_hold():
    probabilities = np.array([[0.11, 0.80, 0.09]])
    values = evaluation.ValueScale(
        class_values=np.array([0, 1, 2]),
        actual_values=np.array([1]),
        first_value=0,
        value_step=1
    )

    scores = evaluation.score_classification(probabilities, np.array([1]), values)

    assert scores[evaluation.CENTRAL_INTERVAL_CALIBRATION_ERROR] == pytest.approx(0.09)
