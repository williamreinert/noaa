import csv
import sqlite3
from datetime import datetime
from pathlib import Path


SOURCE_CSV = Path(__file__).resolve().with_name(
    "StormEvents_details-ftp_v1.0_d2023_c20240117.csv"
)
DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "data.db"
TABLE_NAME = "StormEvents"
BATCH_SIZE = 1000

DATETIME_COLUMNS = {"BEGIN_DATE_TIME", "END_DATE_TIME"}
INTEGER_COLUMNS = {
    "BEGIN_YEARMONTH",
    "BEGIN_DAY",
    "BEGIN_TIME",
    "END_YEARMONTH",
    "END_DAY",
    "END_TIME",
    "EPISODE_ID",
    "EVENT_ID",
    "STATE_FIPS",
    "YEAR",
    "CZ_FIPS",
    "INJURIES_DIRECT",
    "INJURIES_INDIRECT",
    "DEATHS_DIRECT",
    "DEATHS_INDIRECT",
    "CATEGORY",
    "TOR_WIDTH",
    "BEGIN_RANGE",
    "END_RANGE",
}
REAL_COLUMNS = {
    "DAMAGE_PROPERTY",
    "DAMAGE_CROPS",
    "MAGNITUDE",
    "TOR_LENGTH",
    "BEGIN_LAT",
    "BEGIN_LON",
    "END_LAT",
    "END_LON",
}
DAMAGE_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
COLUMN_TYPES = {
    **dict.fromkeys(DATETIME_COLUMNS, "DATETIME"),
    **dict.fromkeys(INTEGER_COLUMNS, "INTEGER"),
    **dict.fromkeys(REAL_COLUMNS, "REAL"),
}


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def convert_value(
    column: str, value: str, row_number: int
) -> int | float | str | None:
    value = value.strip()
    if not value:
        return None

    try:
        if column in DATETIME_COLUMNS:
            return datetime.strptime(value, "%d-%b-%y %H:%M:%S").isoformat(sep=" ")
        if column in INTEGER_COLUMNS:
            return int(value)
        if column in REAL_COLUMNS:
            if column in {"DAMAGE_PROPERTY", "DAMAGE_CROPS"}:
                suffix = value[-1].upper()
                if suffix in DAMAGE_MULTIPLIERS:
                    return float(value[:-1]) * DAMAGE_MULTIPLIERS[suffix]
            return float(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid value in CSV row {row_number}, "
            f"column {column}: {value!r}"
        ) from error

    return value


def create_database() -> int:
    if not SOURCE_CSV.is_file():
        raise FileNotFoundError(f"Storm events CSV not found: {SOURCE_CSV}")

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        columns = next(reader, None)
        if not columns:
            raise ValueError(f"Storm events CSV has no header: {SOURCE_CSV}")
        if len(columns) != len(set(columns)):
            raise ValueError("Storm events CSV contains duplicate column names")

        column_definitions = ", ".join(
            f"{quote_identifier(column)} {COLUMN_TYPES.get(column, 'TEXT')}"
            for column in columns
        )
        insert_columns = ", ".join(quote_identifier(column) for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        insert_sql = (
            f"INSERT INTO {quote_identifier(TABLE_NAME)} "
            f"({insert_columns}) VALUES ({placeholders})"
        )
        create_sql = (
            f"CREATE TABLE {quote_identifier(TABLE_NAME)} ({column_definitions})"
        )

        row_count = 0
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(f"DROP TABLE IF EXISTS {quote_identifier(TABLE_NAME)}")
            connection.execute(create_sql)

            batch = []
            for row_number, row in enumerate(reader, start=2):
                if len(row) != len(columns):
                    raise ValueError(
                        f"CSV row {row_number} has {len(row)} values; "
                        f"expected {len(columns)}"
                    )
                batch.append(
                    tuple(
                        convert_value(column, value, row_number)
                        for column, value in zip(columns, row)
                    )
                )
                if len(batch) >= BATCH_SIZE:
                    connection.executemany(insert_sql, batch)
                    row_count += len(batch)
                    batch.clear()

            if batch:
                connection.executemany(insert_sql, batch)
                row_count += len(batch)

    return row_count


if __name__ == "__main__":
    imported_rows = create_database()
    print(f"Imported {imported_rows:,} storm events into {DATABASE_PATH}")
