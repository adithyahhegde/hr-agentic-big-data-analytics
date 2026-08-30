from __future__ import annotations

import csv
import io


class CsvValidationError(ValueError):
    """A safe, user-actionable CSV validation failure."""


def parse_csv(payload: bytes, *, max_bytes: int, max_rows: int, max_columns: int) -> tuple[list[str], list[dict[str, str]]]:
    if not payload:
        raise CsvValidationError("The uploaded file is empty.")
    if len(payload) > max_bytes:
        raise CsvValidationError("The uploaded file exceeds the configured size limit.")
    if b"\x00" in payload:
        raise CsvValidationError("The uploaded file contains unsupported binary content.")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CsvValidationError("The CSV must be UTF-8 encoded.") from error

    try:
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames
        if not headers:
            raise CsvValidationError("The CSV must include a header row.")
        cleaned_headers = [header.strip() if header else "" for header in headers]
        if not all(cleaned_headers):
            raise CsvValidationError("Column names cannot be blank.")
        if len(cleaned_headers) > max_columns:
            raise CsvValidationError("The CSV exceeds the configured column limit.")
        if len(set(cleaned_headers)) != len(cleaned_headers):
            raise CsvValidationError("Column names must be unique after trimming whitespace.")
        rows = []
        for index, row in enumerate(reader, start=2):
            if index > max_rows + 1:
                raise CsvValidationError("The CSV exceeds the configured profiling row limit.")
            if None in row:
                raise CsvValidationError(f"Row {index} has more values than the header row.")
            rows.append({key.strip(): (value or "").strip() for key, value in row.items()})
    except csv.Error as error:
        raise CsvValidationError("The CSV could not be parsed. Check delimiters and quoting.") from error
    if not rows:
        raise CsvValidationError("The CSV has a header but no data rows.")
    return cleaned_headers, rows
