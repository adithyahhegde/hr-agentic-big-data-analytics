import pytest

from app.services.csv_ingestion import CsvValidationError, parse_csv


def test_parse_csv_rejects_duplicate_trimmed_headers():
    with pytest.raises(CsvValidationError, match="unique"):
        parse_csv(b"employee_id, employee_id\n1,2\n", max_bytes=100, max_rows=10, max_columns=10)


def test_parse_csv_rejects_non_utf8_input():
    with pytest.raises(CsvValidationError, match="UTF-8"):
        parse_csv(b"employee\xff\n1\n", max_bytes=100, max_rows=10, max_columns=10)
