import os
from datetime import datetime
import pandas as pd
import numpy as np

SEASON_NAMES = ["WINTER", "SPRING", "SUMMER", "FALL"]
# a (non movie) work released this many days or less before the next season starts is labeled with that next season
DAYS_TO_NEXT_SEASON = 30

# columns where 0 is not a real value but a placeholder for "unknown"
ZERO_IS_NULL = ["episodes", "duration", "score", "mean_score", "season_year"]
# short categorical columns where words like "None" are a placeholder for "unknown"
PLACEHOLDER_WORD_COLUMNS = ["season", "source", "status", "country_of_origin"]

def save_csv(df, path):
    """
    write to a temporary file first and then swap it in, so a failed write never leaves path half-written
    """

    tmp = f"{path}.tmp"
    try:
        df.to_csv(tmp, index=False, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        print(f"\nError saving {os.path.basename(path)}, the file was left as it was: {e}")
        raise SystemExit(1)

def season_offset(n):
    """
    (season, year) n seasons away from the current one: 0 is the current, -1 the previous and 1 the next
    """

    now = datetime.now()
    i = now.year * 4 + (now.month - 1) // 3 + n
    return SEASON_NAMES[i % 4], i // 4

# shuts out the seasons yet to come, so their works are concatenated only once their season starts. Works without
# season or season_year are kept
def filter_season(df):
    season, year = season_offset(0)
    order = df["season_year"] * 4 + df["season"].str.upper().map({name: i for i, name in enumerate(SEASON_NAMES)})

    return df[~(order > year * 4 + SEASON_NAMES.index(season))]

def sort_by_date(df):
    """
    sort by start_date; the rows without it are placed using the first day of their season_year + season
    """

    start = pd.to_datetime(df["start_date"], errors="coerce")
    season_month = df["season"].str.upper().map({name: i * 3 + 1 for i, name in enumerate(SEASON_NAMES)})
    approx = pd.to_datetime(
        pd.DataFrame({"year": df["season_year"], "month": season_month, "day": 1}), errors="coerce"
    )

    key = start.fillna(approx)
    return df.iloc[key.argsort(kind="stable")]

def sort_final(df, how):
    """how: "date", "title" or null (keep the order the works were added)"""

    if how == "date":
        df = sort_by_date(df)
    elif how == "title":
        df = df.sort_values(by="title", key=lambda col: col.str.lower())

    return df

def merge(old, new):
    """
    old + new, the rows of new replace the ones of old with the same anime_id; start_date as YYYY-MM-DD, sorted by date
    """

    df = pd.concat([old, new], ignore_index=True).drop_duplicates(subset="anime_id", keep="last")
    df["start_date"] = pd.to_datetime(df["start_date"], format="mixed").dt.strftime("%Y-%m-%d")
    return sort_by_date(df)

def clean_invalid(df):
    """
    turn into null the values that only pretend to be data: blank strings, "None"-like words, zeros in ZERO_IS_NULL,
    an end_date before start_date, a season_year more than a year away from start_date and a season on the opposite
    side of the year from start_date. Run it before fill_episodes and fill_season so they can refill what is possible
    """

    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].replace(r"^\s*$", np.nan, regex=True)
    for col in PLACEHOLDER_WORD_COLUMNS:
        df[col] = df[col].replace(r"(?i)^\s*(none|nan|null|n/a)\s*$", np.nan, regex=True)

    df[ZERO_IS_NULL] = df[ZERO_IS_NULL].replace(0, np.nan)

    start = pd.to_datetime(df["start_date"], errors="coerce")
    df.loc[pd.to_datetime(df["end_date"], errors="coerce") < start, "end_date"] = np.nan
    df.loc[(df["season_year"] - start.dt.year).abs() > 1, "season_year"] = np.nan

    season_gap = (df["season"].str.upper().map(dict(zip(SEASON_NAMES, range(4)))) - (start.dt.month - 1) // 3) % 4
    df.loc[season_gap == 2, "season"] = np.nan

    return df

def fill_episodes(df):
    """
    fill the null values in the column "episodes" using "next_episode_number" 
    """

    df = df.copy()
    # Ensure columns are numeric (floats)
    df["episodes"] = pd.to_numeric(df["episodes"], errors="coerce")
    df["next_episode_number"] = pd.to_numeric(df["next_episode_number"], errors="coerce")
    
    # Calculate what the "filled" values SHOULD be: next_ep 5 becomes 4.
    # next_ep 0 (no next episode) or 1 (nothing aired yet) says nothing about the total, so it stays null
    calculated_fills = (df["next_episode_number"] - 1).where(df["next_episode_number"] > 1)
    
    # Fill only the missing values in "episodes" using the calculation
    df["episodes"] = df["episodes"].fillna(calculated_fills)
    
    return df

def fill_season_year(df):
    """
    fill the null values in the column "season_year" with the year of "start_date". Without start_date it stays null
    """

    df = df.copy()
    df["season_year"] = df["season_year"].fillna(pd.to_datetime(df["start_date"], errors="coerce").dt.year)

    return df

def fill_season(df):
    """
    fill the null values in the column "season" using "start_date". Movies get the season of their month, any other
    type gets the next season if it starts DAYS_TO_NEXT_SEASON days or less after start_date. Without start_date it stays null
    """

    df = df.copy()
    start = pd.to_datetime(df["start_date"], errors="coerce")
    is_movie = df["type"].str.lower() == "movie"

    shifted = start.where(is_movie, start + pd.Timedelta(days=DAYS_TO_NEXT_SEASON))
    df["season"] = df["season"].fillna(((shifted.dt.month - 1) // 3).map(dict(enumerate(SEASON_NAMES))))

    return df

def clean(df):
    """
    every cleaning step for freshly fetched works, in order. Needs the column "next_episode_number", which is dropped
    """

    df = fill_season(fill_season_year(fill_episodes(clean_invalid(df))))
    return df.drop("next_episode_number", axis=1)

