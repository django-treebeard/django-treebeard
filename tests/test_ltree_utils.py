import time

import pytest

from treebeard.ltree import InvalidLabelConstraints, generate_label


class TestGenerateLabel:
    def test_invalid_before_after(self):
        with pytest.raises(InvalidLabelConstraints):
            # Before is less than after
            generate_label(before="A", after="B", skip=set())

        with pytest.raises(InvalidLabelConstraints):
            # Before is equal to after
            generate_label(before="A", after="A", skip=set())

    def test_no_constraint(self):
        assert generate_label(skip=set()) == "A"

    def test_no_after(self):
        assert generate_label(before="A", skip=set()) == "0"
        assert generate_label(before="ABCDE", skip=set()) == "0"

    def test_no_before(self):
        assert generate_label(after="A", skip=set()) == "B"

    def test_reduces_char_count_where_possible(self):
        assert generate_label(after="ABB", skip=set()) == "B"
        assert generate_label(after="ZYX", skip=set()) == "ZZ"
        assert generate_label(after="ZYX", before="ZZ", skip=set()) == "ZYY"

    def test_adds_char_if_needed(self):
        assert generate_label(before="AA", after="A", skip=set()) == "A0"
        assert generate_label(before="B", after="AZ", skip=set()) == "AZ0"

    def test_respects_skip(self):
        assert generate_label(before="AA", after="A", skip={"A0"}) == "A1"
        assert generate_label(before="B", after="AZ", skip={"AZ0"}) == "AZ1"
        assert generate_label(after="ZYX", skip={"ZZ"}) == "ZYY"

    def test_large_string(self):
        # Check that we don't have exponential time for large strings
        start = time.perf_counter()
        res = generate_label(before="A" * 59999 + "B", after="A" * 60000, skip=set())
        time_taken = time.perf_counter() - start
        assert time_taken < 0.5  # Conservative to allow for flakiness on CI
        assert res == "A" * 60000 + "0"

        start = time.perf_counter()
        res = generate_label(before="B", after="A" * 60000, skip=set())
        time_taken = time.perf_counter() - start
        assert time_taken < 0.05
        assert res == "AB"
