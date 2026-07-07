"""Tests for the network-free core of the commit-era pinner."""

from datetime import date, datetime, timezone

import pytest

from lazarus.pinner import ReleaseInfo, _requirement_name, as_cutoff, select_version


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


# A small synthetic release history resembling a real package's timeline.
HISTORY = [
    ReleaseInfo("0.9.0", _utc(2016, 1, 10)),
    ReleaseInfo("1.0.0", _utc(2017, 6, 1)),
    ReleaseInfo("1.9.0", _utc(2018, 5, 20)),
    ReleaseInfo("1.10.0", _utc(2018, 11, 2)),
    ReleaseInfo("2.0.0", _utc(2020, 1, 15)),
    ReleaseInfo("2.1.0rc1", _utc(2020, 3, 1)),
]


def test_picks_newest_on_or_before_cutoff():
    assert select_version(HISTORY, date(2019, 1, 1)) == "1.10.0"


def test_pep440_ordering_beats_lexical():
    # 1.10 must outrank 1.9 even though "1.9" > "1.10" lexically.
    assert select_version(HISTORY, date(2018, 12, 31)) == "1.10.0"


def test_cutoff_is_inclusive_of_release_day():
    # A release published on the cutoff date itself should qualify.
    assert select_version(HISTORY, date(2017, 6, 1)) == "1.0.0"


def test_returns_none_when_nothing_before_cutoff():
    assert select_version(HISTORY, date(2015, 1, 1)) is None


def test_prereleases_excluded_by_default():
    assert select_version(HISTORY, date(2020, 6, 1)) == "2.0.0"


def test_prereleases_included_when_allowed():
    assert select_version(HISTORY, date(2020, 6, 1), allow_prerelease=True) == "2.1.0rc1"


def test_yanked_excluded_by_default_but_optional():
    hist = [
        ReleaseInfo("1.0.0", _utc(2018, 1, 1)),
        ReleaseInfo("1.1.0", _utc(2018, 6, 1), yanked=True),
    ]
    assert select_version(hist, date(2019, 1, 1)) == "1.0.0"
    assert select_version(hist, date(2019, 1, 1), allow_yanked=True) == "1.1.0"


def test_invalid_versions_are_skipped():
    hist = [
        ReleaseInfo("not-a-version", _utc(2018, 1, 1)),
        ReleaseInfo("1.2.3", _utc(2018, 2, 1)),
    ]
    assert select_version(hist, date(2019, 1, 1)) == "1.2.3"


def test_as_cutoff_makes_bare_date_end_of_day_utc():
    dt = as_cutoff(date(2020, 5, 4))
    assert dt.tzinfo == timezone.utc
    assert (dt.hour, dt.minute) == (23, 59)


@pytest.mark.parametrize(
    "req,expected",
    [
        ("numpy", "numpy"),
        ("scipy>=1.4", "scipy"),
        ("tensorflow==1.12.0", "tensorflow"),
        ("requests[security]>=2", "requests"),
        ("pkg ; python_version<'3.7'", "pkg"),
    ],
)
def test_requirement_name_extraction(req, expected):
    assert _requirement_name(req) == expected
