import os
from io import StringIO
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA_PATH = ROOT / "hw_assignment_data.csv"
TABLE_NAME = "hw_assignment_data"
CHUNK_SIZE = 50_000

BOOLEAN_COLUMNS = {
    "is_renewal",
    "is_faulty_lead",
    "is_small_fleet",
    "is_webstore_upsell_opportunity",
}

NUMERIC_COLUMNS = {
    "percent_of_total",
    "sql",
    "sql_pipe",
    "total_opp_value",
    "sql_deal_progression",
    "sqo",
    "closed_won",
    "closed_lost",
    "closed_won_pipe",
    "closed_lost_pipe",
}


def postgres_type(column: str) -> str:
    if column in BOOLEAN_COLUMNS:
        return "BOOLEAN"
    if column in NUMERIC_COLUMNS:
        return "DOUBLE PRECISION"
    if column.endswith("_timestamp"):
        return "TIMESTAMPTZ"
    if column.endswith("_date"):
        return "DATE"
    return "TEXT"


def normalize_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk = chunk.where(pd.notna(chunk), None)

    for column in BOOLEAN_COLUMNS:
        if column not in chunk.columns:
            continue
        chunk[column] = chunk[column].map(
            {"true": True, "false": False, True: True, False: False}
        )

    for column in chunk.columns:
        if column.endswith("_date"):
            parsed = pd.to_datetime(chunk[column], errors="coerce")
            chunk[column] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), None)
        elif column.endswith("_timestamp"):
            parsed = pd.to_datetime(chunk[column], errors="coerce", utc=True)
            chunk[column] = (
                parsed.dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str.slice(0, 23) + "Z"
            ).where(parsed.notna(), None)

    return chunk


def create_table(cur: psycopg2.extensions.cursor, columns: list[str]) -> None:
    cur.execute(
        sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(TABLE_NAME))
    )

    column_defs = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(column), sql.SQL(postgres_type(column)))
        for column in columns
    )
    cur.execute(
        sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(TABLE_NAME), column_defs
        )
    )


def copy_chunk(
    cur: psycopg2.extensions.cursor, columns: list[str], chunk: pd.DataFrame
) -> None:
    buffer = StringIO()
    chunk.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    column_list = sql.SQL(", ").join(map(sql.Identifier, columns))
    copy_sql = sql.SQL(
        "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
    ).format(sql.Identifier(TABLE_NAME), column_list)

    cur.copy_expert(copy_sql.as_string(cur.connection), buffer)


def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    header = pd.read_csv(DATA_PATH, nrows=0, low_memory=False)
    columns = header.columns.tolist()

    total_rows = 0
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            print(f"Creating table `{TABLE_NAME}` with {len(columns)} columns...")
            create_table(cur, columns)
            conn.commit()

            print(f"Loading data from {DATA_PATH.name} in chunks of {CHUNK_SIZE:,}...")
            for chunk_number, chunk in enumerate(
                pd.read_csv(DATA_PATH, chunksize=CHUNK_SIZE, low_memory=False),
                start=1,
            ):
                chunk = normalize_chunk(chunk)
                copy_chunk(cur, columns, chunk)
                conn.commit()

                total_rows += len(chunk)
                print(f"  chunk {chunk_number}: {total_rows:,} rows loaded")

            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(TABLE_NAME)))
            row_count = cur.fetchone()[0]

    print(f"Done. `{TABLE_NAME}` contains {row_count:,} rows.")


if __name__ == "__main__":
    main()
