import os
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

OUTPUT_PATH = ROOT / "sql_pipeline_by_quarter.png"
US_OUTPUT_PATH = ROOT / "sql_pipeline_us_by_quarter.png"
OTHER_REGIONS_OUTPUT_PATH = ROOT / "sql_pipeline_other_regions_by_quarter.png"
YOY_OUTPUT_PATH = ROOT / "pipeline_yoy_growth.csv"
REGION_TABLE_PATH = ROOT / "pipeline_by_region_quarter.csv"
US_VS_REST_PIE_PATH = ROOT / "pipeline_us_vs_rest_by_year.png"
SECTOR_PIE_PATH = ROOT / "pipeline_public_vs_private_by_year.png"
SEGMENT_PIE_PATH = ROOT / "pipeline_by_oppty_segment_by_year.png"

PIPELINE_SUMMARY_SQL = "SELECT * FROM pipeline_summary()"
PIPELINE_BY_REGION_QUARTER_SQL = "SELECT * FROM pipeline_by_region_quarter()"
PIPELINE_BY_SECTOR_YEAR_SQL = "SELECT * FROM pipeline_by_sector_year()"
PIPELINE_BY_SEGMENT_YEAR_SQL = "SELECT * FROM pipeline_by_segment_year()"

SEGMENT_COLORS = {
    "ENT - SEL": "#1f77b4",
    "ENT - COR": "#ff7f0e",
    "ENT - STR": "#2ca02c",
    "MM": "#d62728",
    "CML": "#9467bd",
}


def sort_quarters(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["quarter"] = df["quarter_year"].str.extract(r"(Q\d+)", expand=False)
    df["year_num"] = df["year"].str.extract(r"FY(\d+)", expand=False).astype(int)
    df["quarter_num"] = df["quarter"].str.extract(r"Q(\d+)", expand=False).astype(int)
    return df.sort_values(["year_num", "quarter_num"]).reset_index(drop=True)


def load_pipeline_by_quarter() -> pd.DataFrame:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        df = pd.read_sql(PIPELINE_SUMMARY_SQL, conn)

    return sort_quarters(df)


def load_pipeline_by_region_quarter() -> pd.DataFrame:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        df = pd.read_sql(PIPELINE_BY_REGION_QUARTER_SQL, conn)

    return sort_quarters(df)


def load_pipeline_by_sector_year() -> pd.DataFrame:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        df = pd.read_sql(PIPELINE_BY_SECTOR_YEAR_SQL, conn)

    df["year_num"] = df["year"].str.extract(r"FY(\d+)", expand=False).astype(int)
    return df.sort_values(["year_num", "account_sector"]).reset_index(drop=True)


def load_pipeline_by_segment_year() -> pd.DataFrame:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        df = pd.read_sql(PIPELINE_BY_SEGMENT_YEAR_SQL, conn)

    df["year_num"] = df["year"].str.extract(r"FY(\d+)", expand=False).astype(int)
    return df.sort_values(["year_num", "oppty_segment"]).reset_index(drop=True)


def calculate_yoy_growth(df: pd.DataFrame) -> pd.DataFrame:
    pipeline = df[["quarter_year", "year", "quarter", "year_num", "quarter_num", "sql_pipeline"]].copy()

    prior_year = pipeline.rename(
        columns={
            "quarter_year": "prior_quarter_year",
            "sql_pipeline": "prior_year_pipeline",
        }
    )[["quarter", "year_num", "prior_quarter_year", "prior_year_pipeline"]]
    prior_year["year_num"] = prior_year["year_num"] + 1

    result = pipeline.merge(prior_year, on=["quarter", "year_num"], how="left")
    result["yoy_growth_pct"] = (
        (result["sql_pipeline"] - result["prior_year_pipeline"])
        / result["prior_year_pipeline"]
        * 100
    )
    result.loc[result["prior_year_pipeline"].isna() | (result["prior_year_pipeline"] == 0), "yoy_growth_pct"] = pd.NA

    return result.sort_values(["year_num", "quarter_num"]).reset_index(drop=True)


def print_yoy_growth_table(df: pd.DataFrame) -> pd.DataFrame:
    yoy = calculate_yoy_growth(df)
    display = yoy[["quarter_year", "sql_pipeline", "prior_year_pipeline", "yoy_growth_pct"]].copy()
    display["sql_pipeline"] = display["sql_pipeline"].map(lambda x: f"${x:,.2f}")
    display["prior_year_pipeline"] = display["prior_year_pipeline"].map(
        lambda x: "N/A" if pd.isna(x) else f"${x:,.2f}"
    )
    display["yoy_growth_pct"] = display["yoy_growth_pct"].map(
        lambda x: "N/A" if pd.isna(x) else f"{x:,.1f}%"
    )
    display = display.rename(
        columns={
            "quarter_year": "quarter",
            "sql_pipeline": "pipeline",
            "prior_year_pipeline": "prior_year_pipeline",
            "yoy_growth_pct": "yoy_growth",
        }
    )

    print("\nYear-over-year pipeline growth since FY24 Q1")
    print("=" * 90)
    print(display.to_string(index=False))
    print("=" * 90)

    export = yoy[["quarter_year", "sql_pipeline", "prior_year_pipeline", "yoy_growth_pct"]].rename(
        columns={
            "quarter_year": "quarter",
            "sql_pipeline": "pipeline",
            "yoy_growth_pct": "yoy_growth_pct",
        }
    )
    export.to_csv(YOY_OUTPUT_PATH, index=False)
    print(f"Table saved to {YOY_OUTPUT_PATH.resolve()}")
    return yoy


def print_pipeline_table(df: pd.DataFrame) -> None:
    table = df[["year", "quarter", "quarter_year", "sql_pipeline"]].copy()
    table["sql_pipeline"] = table["sql_pipeline"].map(lambda x: f"${x:,.2f}")

    print("SQL pipeline by quarter and year (ascending order)")
    print("=" * 70)
    print(table.to_string(index=False))
    print("=" * 70)
    print(f"Total: ${df['sql_pipeline'].sum():,.2f}")


def format_dollars(value: float) -> str:
    return f"${value:,.0f}"


def annotate_bars(ax, x_positions, y_values) -> None:
    for x, y in zip(x_positions, y_values, strict=True):
        if y == 0:
            continue
        ax.annotate(
            format_dollars(y),
            (x, y),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=8,
        )


def style_bar_axes(ax, quarter_labels, *, title: str, xlabel: str = "Quarter") -> None:
    dollar_formatter = plt.FuncFormatter(lambda x, _: format_dollars(x))

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Pipeline Amount ($)")
    ax.yaxis.set_major_formatter(dollar_formatter)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_xticks(range(len(quarter_labels)))
    ax.set_xticklabels(quarter_labels, rotation=45, ha="right")


def plot_pipeline_by_quarter(df: pd.DataFrame) -> None:
    fy24 = df[df["year"] == "FY24"]
    fy24_labels = fy24["quarter_year"].tolist()
    all_labels = df["quarter_year"].tolist()

    fig, (ax_fy24, ax_all) = plt.subplots(
        2,
        1,
        figsize=(12, 10),
        gridspec_kw={"height_ratios": [1, 2]},
    )

    fy24_x = range(len(fy24_labels))
    ax_fy24.bar(fy24_x, fy24["sql_pipeline"], color="#2ca02c")
    style_bar_axes(ax_fy24, fy24_labels, title="FY24 SQL Pipeline (Zoomed View)")
    annotate_bars(ax_fy24, fy24_x, fy24["sql_pipeline"])

    all_x = range(len(all_labels))
    ax_all.bar(all_x, df["sql_pipeline"], color="#1f77b4")
    style_bar_axes(
        ax_all,
        all_labels,
        title="Total SQL Pipeline by Quarter (FY24–FY26)",
        xlabel="Op Created Quarter",
    )

    fy24_indices = [i for i, label in enumerate(all_labels) if label in fy24_labels]
    for i in fy24_indices:
        value = df.iloc[i]["sql_pipeline"]
        if value == 0:
            continue
        ax_all.annotate(
            format_dollars(value),
            (i, value),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=8,
            color="#2ca02c",
            fontweight="bold",
        )

    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    print(f"Chart saved to {OUTPUT_PATH.resolve()}")
    plt.show()
    return fig


def region_pivot(df: pd.DataFrame) -> pd.DataFrame:
    quarter_order = (
        df[["quarter_year", "year_num", "quarter_num"]]
        .drop_duplicates()
        .sort_values(["year_num", "quarter_num"])["quarter_year"]
        .tolist()
    )

    return (
        df.pivot(index="quarter_year", columns="region", values="sql_pipeline")
        .reindex(quarter_order)
        .fillna(0)
    )


def plot_single_bar(
    ax,
    quarter_labels,
    values,
    *,
    title: str,
    color: str = "#1f77b4",
) -> None:
    x = range(len(quarter_labels))
    ax.bar(x, values, color=color)
    style_bar_axes(ax, quarter_labels, title=title, xlabel="Op Created Quarter")


def plot_pipeline_us(df: pd.DataFrame) -> None:
    pivot = region_pivot(df)
    quarter_labels = pivot.index.tolist()
    us_values = pivot["United States"]

    fig, ax = plt.subplots(figsize=(12, 6))
    plot_single_bar(
        ax,
        quarter_labels,
        us_values,
        title="SQL Pipeline — United States by Op Created Quarter (FY24–FY26)",
        color="#1f77b4",
    )
    fig.tight_layout()
    fig.savefig(US_OUTPUT_PATH, dpi=150)
    print(f"Chart saved to {US_OUTPUT_PATH.resolve()}")
    plt.show()
    return fig


def plot_pipeline_other_regions(df: pd.DataFrame) -> None:
    pivot = region_pivot(df)
    other_regions = [col for col in pivot.columns if col != "United States"]
    quarter_labels = pivot.index.tolist()

    fig, ax = plt.subplots(figsize=(14, 8))
    x = np.arange(len(quarter_labels))
    bar_width = 0.8 / len(other_regions)

    for i, region in enumerate(other_regions):
        offset = (i - (len(other_regions) - 1) / 2) * bar_width
        ax.bar(x + offset, pivot[region], bar_width, label=region)

    style_bar_axes(
        ax,
        quarter_labels,
        title="SQL Pipeline — All Other Regions by Op Created Quarter (FY24–FY26)",
        xlabel="Op Created Quarter",
    )
    ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(OTHER_REGIONS_OUTPUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {OTHER_REGIONS_OUTPUT_PATH.resolve()}")
    plt.show()
    return fig


def print_region_pipeline_table(df: pd.DataFrame) -> pd.DataFrame:
    table = df[["region", "quarter_year", "sql_pipeline"]].copy()
    table = table.rename(
        columns={
            "quarter_year": "quarter",
            "sql_pipeline": "pipeline",
        }
    )

    display = table.copy()
    display["pipeline"] = display["pipeline"].map(lambda x: f"${x:,.2f}")

    print("\nPipeline by region and quarter")
    print("=" * 70)
    print(display.to_string(index=False))
    print("=" * 70)
    print(f"Rows: {len(table):,}")

    table.to_csv(REGION_TABLE_PATH, index=False)
    print(f"Table saved to {REGION_TABLE_PATH.resolve()}")
    return table


def us_vs_rest_by_year(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.copy()
    grouped["market"] = np.where(
        grouped["region"] == "United States",
        "United States",
        "Rest of Countries",
    )
    return (
        grouped.groupby(["year", "market"], as_index=False)["sql_pipeline"]
        .sum()
        .sort_values(["year", "market"])
    )


def pie_autopct(values: list[float]):
    total = sum(values)

    def formatter(pct: float) -> str:
        amount = pct * total / 100.0
        return f"{pct:.1f}%\n{format_dollars(amount)}"

    return formatter


def plot_us_vs_rest_pie_charts(df: pd.DataFrame) -> None:
    summary = us_vs_rest_by_year(df)
    years = ["FY24", "FY25", "FY26"]
    colors = {"United States": "#1f77b4", "Rest of Countries": "#ff7f0e"}

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, year in zip(axes, years, strict=True):
        year_data = summary[summary["year"] == year]
        labels = year_data["market"].tolist()
        values = year_data["sql_pipeline"].tolist()
        slice_colors = [colors[label] for label in labels]

        if sum(values) == 0:
            ax.text(0.5, 0.5, "No pipeline", ha="center", va="center")
            ax.set_title(f"{year}")
            ax.axis("off")
            continue

        ax.pie(
            values,
            labels=labels,
            colors=slice_colors,
            autopct=pie_autopct(values),
            startangle=90,
            textprops={"fontsize": 9},
        )
        ax.set_title(f"{year}\nTotal: {format_dollars(sum(values))}")

    fig.suptitle("SQL Pipeline: United States vs Rest of Countries", fontsize=14)
    fig.tight_layout()
    fig.savefig(US_VS_REST_PIE_PATH, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {US_VS_REST_PIE_PATH.resolve()}")
    plt.show()
    return fig


def print_us_vs_rest_table(df: pd.DataFrame) -> None:
    summary = us_vs_rest_by_year(df)
    display = summary.copy()
    display["sql_pipeline"] = display["sql_pipeline"].map(lambda x: f"${x:,.2f}")
    display = display.rename(columns={"market": "region_group", "sql_pipeline": "pipeline"})

    print("\nPipeline: United States vs Rest of Countries by fiscal year")
    print("=" * 70)
    print(display.to_string(index=False))
    print("=" * 70)


def plot_sector_pie_charts(df: pd.DataFrame) -> None:
    years = ["FY24", "FY25", "FY26"]
    colors = {"Private": "#1f77b4", "Public": "#ff7f0e"}

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, year in zip(axes, years, strict=True):
        year_data = df[df["year"] == year]
        labels = year_data["account_sector"].tolist()
        values = year_data["sql_pipeline"].tolist()
        slice_colors = [colors[label] for label in labels]

        if sum(values) == 0:
            ax.text(0.5, 0.5, "No pipeline", ha="center", va="center")
            ax.set_title(f"{year}")
            ax.axis("off")
            continue

        ax.pie(
            values,
            labels=labels,
            colors=slice_colors,
            autopct=pie_autopct(values),
            startangle=90,
            textprops={"fontsize": 9},
        )
        ax.set_title(f"{year}\nTotal: {format_dollars(sum(values))}")

    fig.suptitle("SQL Pipeline: Private vs Public Sector", fontsize=14)
    fig.tight_layout()
    fig.savefig(SECTOR_PIE_PATH, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {SECTOR_PIE_PATH.resolve()}")
    plt.show()
    return fig


def plot_segment_pie_charts(df: pd.DataFrame) -> None:
    years = ["FY24", "FY25", "FY26"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for ax, year in zip(axes, years, strict=True):
        year_data = (
            df[df["year"] == year]
            .sort_values("sql_pipeline", ascending=False)
            .reset_index(drop=True)
        )
        labels = year_data["oppty_segment"].tolist()
        values = year_data["sql_pipeline"].tolist()
        slice_colors = [SEGMENT_COLORS[label] for label in labels]

        if sum(values) == 0:
            ax.text(0.5, 0.5, "No pipeline", ha="center", va="center")
            ax.set_title(f"{year}")
            ax.axis("off")
            continue

        ax.pie(
            values,
            labels=labels,
            colors=slice_colors,
            autopct=pie_autopct(values),
            startangle=90,
            textprops={"fontsize": 8},
        )
        ax.set_title(f"{year}\nTotal: {format_dollars(sum(values))}")

    fig.suptitle("SQL Pipeline by Oppty Segment", fontsize=14)
    fig.tight_layout()
    fig.savefig(SEGMENT_PIE_PATH, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {SEGMENT_PIE_PATH.resolve()}")
    plt.show()
    return fig


def open_chart(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform == "win32":
        subprocess.run(["start", "", str(path)], shell=True, check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def main() -> None:
    df = load_pipeline_by_quarter()
    plot_pipeline_by_quarter(df)
    open_chart(OUTPUT_PATH)
    print_pipeline_table(df)
    print_yoy_growth_table(df)

    region_df = load_pipeline_by_region_quarter()
    plot_pipeline_us(region_df)
    open_chart(US_OUTPUT_PATH)
    plot_pipeline_other_regions(region_df)
    open_chart(OTHER_REGIONS_OUTPUT_PATH)
    print_region_pipeline_table(region_df)
    plot_us_vs_rest_pie_charts(region_df)
    open_chart(US_VS_REST_PIE_PATH)
    print_us_vs_rest_table(region_df)

    sector_df = load_pipeline_by_sector_year()
    plot_sector_pie_charts(sector_df)
    open_chart(SECTOR_PIE_PATH)

    segment_df = load_pipeline_by_segment_year()
    plot_segment_pie_charts(segment_df)
    open_chart(SEGMENT_PIE_PATH)


if __name__ == "__main__":
    main()
