from misc.utils import strip_ts_basename


def test_strip_ts_14_digits_with_underscore():
    assert strip_ts_basename("REPORT_20251105120450.xlsx") == "REPORT.xlsx"


def test_strip_ts_14_digits_with_dot():
    assert strip_ts_basename("REPORT.20251105120450.xlsx") == "REPORT.xlsx"


def test_strip_ts_8_digits_with_underscore():
    assert strip_ts_basename("REPORT_20251105.xlsx") == "REPORT.xlsx"


def test_not_strip_ts_with_T_separator():
    # Current patterns do not handle "T" format; treat it as part of the base.
    assert strip_ts_basename("REPORT_20251105T120450.xlsx") == "REPORT_20251105T120450.xlsx"


def test_not_strip_ts_with_milliseconds():
    assert strip_ts_basename("REPORT_20251105120450123.xlsx") == "REPORT_20251105120450123.xlsx"


def test_not_strip_when_ts_not_at_end():
    assert strip_ts_basename("REPORT_20251105120450_extra.xlsx") == "REPORT_20251105120450_extra.xlsx"

