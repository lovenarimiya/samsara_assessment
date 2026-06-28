from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent / "hw_assignment_data.csv"


def main() -> None:
    df = pd.read_csv(DATA_PATH, low_memory=False)

    print("=" * 60)
    print("Dataset overview")
    print("=" * 60)
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print()

    print("Column names and dtypes")
    print("-" * 60)
    print(df.dtypes)
    print()

    print("First 5 rows")
    print("-" * 60)
    print(df.head())
    print()

    print("Missing values (top 20 columns by null count)")
    print("-" * 60)
    missing = df.isna().sum().sort_values(ascending=False)
    print(missing.head(20))
    print(f"Total missing cells: {missing.sum():,}")
    print()

    numeric_cols = df.select_dtypes(include="number").columns
    print(f"Numeric summary ({len(numeric_cols)} columns)")
    print("-" * 60)
    print(df[numeric_cols].describe().T)
    print()

    object_cols = df.select_dtypes(include="object").columns
    print(f"Categorical summary ({len(object_cols)} columns)")
    print("-" * 60)
    for col in object_cols[:10]:
        print(f"\n{col} (unique: {df[col].nunique():,})")
        print(df[col].value_counts(dropna=False).head(5))


if __name__ == "__main__":
    main()
