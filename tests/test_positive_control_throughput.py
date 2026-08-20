"""Tests for the PR auditor positive-control fixture. Throwaway branch."""

from automation.positive_control.throughput import last_n_sprints, mean_throughput


def test_last_n_sprints_returns_exactly_n() -> None:
    assert last_n_sprints([1.0, 2.0, 3.0, 4.0, 5.0], 3) == [3.0, 4.0, 5.0]


def test_last_n_sprints_single_value() -> None:
    assert last_n_sprints([1.0, 2.0, 3.0], 1) == [3.0]


def test_last_n_sprints_more_than_available() -> None:
    assert last_n_sprints([1.0, 2.0], 5) == [1.0, 2.0]


def test_last_n_sprints_non_positive_window() -> None:
    assert last_n_sprints([1.0, 2.0], 0) == []


def test_mean_throughput_averages_the_window() -> None:
    assert mean_throughput([1.0, 2.0, 3.0, 4.0], 2) == 3.5


def test_mean_throughput_empty_window() -> None:
    assert mean_throughput([], 3) == 0.0
