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

        with pytest.raises(InvalidLabelConstraints):
            # There is no semantic gap between A and A0
            generate_label(before="A0", after="A", skip=set())

    def test_no_label_sorts_before_the_first_character_of_the_alphabet(self):
        with pytest.raises(InvalidLabelConstraints):
            generate_label(before="0", skip=set())

        # There is still room before 00, so existing nodes don't need moving out of the way
        assert generate_label(before="00", skip=set()) == "0"
        assert generate_label(before="000", skip=set()) == "0"

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
