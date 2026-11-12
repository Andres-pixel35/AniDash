import os
from datetime import datetime
import pandas as pd
import numpy as np
from api.anilist import RELATIONS, SEASON_NAMES

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

def read_csv(path):
    """
    pd.read_csv for the files built from build_row. A relation column with a single id per row would be read as float
    and saved back as "3009.0", so they are read as strings
    """

    return pd.read_csv(path, dtype={r.lower(): str for r in RELATIONS})

def season_offset(n):
    """
    (season, year) n seasons away from the current one: 0 is the current, -1 the previous and 1 the next
    """

    now = datetime.now()
    i = now.year * 4 + (now.month - 1) // 3 + n
    return SEASON_NAMES[i % 4], i // 4

def season_filters(season, year):
    """
    AniList filters for the works of season: by its season and by its start date, since AniList has no season for some
    works. The date bounds leave out a start date with only the year, which says nothing about the season
    """

    month = SEASON_NAMES.index(season) * 3 + 1
    return [f"season: {season}, seasonYear: {year}",
            f"startDate_greater: {year * 10000 + month * 100 - 1}, startDate_lesser: {year * 10000 + (month + 3) * 100}"]

def year_only_filter(year):
    """
    AniList filter for the works of year whose start date has only the year (YYYY0000), no season filter catches them
    """

    return f"startDate_greater: {year - 1}9999, startDate_lesser: {year}0001"

# shuts out the seasons yet to come, so their works are concatenated only once their season starts. Works without
# season_year are kept, without season only a later year shuts them out. Works in kept_ids (already in anime.csv) are
# kept too, so a work whose release moved to a later season still gets its new information
def filter_season(df, kept_ids):
    season, year = season_offset(0)
    order = df["season_year"] * 4 + df["season"].str.upper().map({name: i for i, name in enumerate(SEASON_NAMES)}).fillna(0)

    return df[~(order > year * 4 + SEASON_NAMES.index(season)) | df["anime_id"].isin(kept_ids)]

def sort_by_date(df):
    """
    sort by start_date; the rows without it are placed using the first day of their season_year + season, or on January 1
    of their season_year when they have no season either
    """

    start = pd.to_datetime(df["start_date"], errors="coerce")
    season_month = df["season"].str.upper().map({name: i * 3 + 1 for i, name in enumerate(SEASON_NAMES)}).fillna(1)
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
    old + new, the rows of new replace the ones of old with the same anime_id; start_date and end_date as YYYY-MM-DD,
    sorted by date. old can be None (no anime.csv yet), pd.concat skips it
    """

    df = pd.concat([old, new], ignore_index=True)
    # one type for the key, so 123 and "123" are the same work. A missing or non numeric id raises before anything is saved
    df = df.astype({"anime_id": "int64"}).drop_duplicates(subset="anime_id", keep="last")
    for col in ["start_date", "end_date"]:
        df[col] = pd.to_datetime(df[col], format="mixed").dt.strftime("%Y-%m-%d")
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

