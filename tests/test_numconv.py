import string

import pytest

from treebeard.numconv import NumConv


@pytest.mark.parametrize(
    ("num", "chars"),
    [
        (0, "0"),
        (1, "1"),
        (26, "Q"),
        (27, "R"),
        (46, "1A"),
        (999, "RR"),
        (10560, "85C"),
    ],
)
def test_numconv(num, chars):
    conv = NumConv(string.digits + string.ascii_uppercase)
    assert conv.int2str(num) == chars
    assert conv.str2int(chars) == num
