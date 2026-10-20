import html
import os
import re
import numpy as np
import pandas as pd
import streamlit as st

UNKNOWN = "Unknown"

# only columns that describe the work itself; metadata (covers, banner, hashtag, collected_at, updated_at,
# data_source...) is dropped on load so no page can show it by accident
RAW_COLUMNS = [
    "anime_id", "title", "english_title", "japanese_title", "synonyms", "type", "episodes", "duration", "status",
    "source", "season", "season_year", "studios", "main_studios", "genres", "tags", "score", "mean_score",
    "popularity", "favorites", "watching", "completed", "on_hold", "dropped", "plan_to_watch", "start_date",
    "end_date", "synopsis", "country_of_origin", "main_characters", "main_staff", "streaming_sites", "site_url",
]
NUMERIC_COLUMNS = [
    "episodes", "duration", "season_year", "score", "mean_score", "popularity", "favorites", "watching",
    "completed", "on_hold", "dropped", "plan_to_watch",
]
CATEGORY_COLUMNS = ["type", "status", "source", "season", "country_of_origin"]
LIST_COLUMNS = ["synonyms", "studios", "main_studios", "genres", "tags", "main_characters", "streaming_sites"]
LIST_LIKE = LIST_COLUMNS + ["main_staff", "studio_list"]
# links AniList files under "streaming" that are not streaming services
NOT_STREAMING = {"Official Site", "Twitter", "X"}

CODE_LABELS = {
    "TV": "TV", "TV_SHORT": "TV Short", "OVA": "OVA", "ONA": "ONA",
    "JP": "Japan", "KR": "South Korea", "CN": "China", "TW": "Taiwan",
}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]
# each format keeps its colour in every chart; Catppuccin Latte accents, charts swap them for Mocha in dark mode
FORMAT_COLORS = {
    "TV": "#8839EF", "Movie": "#1E66F5", "ONA": "#179299", "OVA": "#FE640B", "TV Short": "#EA76CB",
    "Special": "#40A02B", "Music": "#DF8E1D", UNKNOWN: "#8C8FA1",
}
FORMAT_ORDER = list(FORMAT_COLORS)[:-1]
LENGTH_BINS = [0, 1, 13, 26, 52, 100, np.inf]
LENGTH_ORDER = ["1 episode", "2-13 eps", "14-26 eps", "27-52 eps", "53-100 eps", "100+ eps"]

# readable names for every column a page may show
LABELS = {
    "name": "Title", "title": "Title (romaji)", "english_title": "English title", "japanese_title": "Japanese title",
    "type": "Format", "episodes": "Episodes", "duration": "Minutes per episode", "watch_hours": "Total hours",
    "length": "Length", "status": "Airing status", "source": "Source material", "season": "Season",
    "year": "Year", "decade": "Decade", "start_date": "Start date", "end_date": "End date",
    "studio_list": "Studios", "genres": "Genres", "tags": "Tags", "score": "Score",
    "mean_score": "Mean user score", "popularity": "Popularity (AniList users)", "favorites": "Favorites",
    "favorite_rate": "Favorites per 1k users", "watching": "Watching", "completed": "Completed",
    "on_hold": "On hold", "dropped": "Dropped", "plan_to_watch": "Plan to watch",
    "completion_rate": "Completion rate", "drop_rate": "Drop rate", "country_of_origin": "Country",
    "main_characters": "Main characters", "main_staff": "Key staff", "streaming_sites": "Streaming on",
    "synopsis": "Synopsis", "site_url": "AniList page",
}


def _pretty(value):
    if not isinstance(value, str) or not value.strip():
        return UNKNOWN
    value = value.strip()
    return CODE_LABELS.get(value.upper(), value.replace("_", " ").title())


def _split(value):
    if not isinstance(value, str):
        return []
    return list(dict.fromkeys(part.strip() for part in value.split(";") if part.strip()))


def _clean_synopsis(value):
    if not isinstance(value, str) or not value.strip():
        return np.nan
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def _parse_staff(value):
    """'Name (Role);Name2 (Role (eps 1-3))' -> [(name, role)], role cut to its first part ('Role')"""
    people = []
    for item in _split(value):
        name, _, role = item.partition(" (")
        role = role.rstrip(")").split(" (")[0].strip()
        people.append((name.strip(), role or UNKNOWN))
    return people


def prepare(raw):
    df = raw[RAW_COLUMNS].copy()

    for col in CATEGORY_COLUMNS:
        df[col] = df[col].map(_pretty)
    for col in LIST_COLUMNS:
        df[col] = df[col].map(_split)
    df["streaming_sites"] = df["streaming_sites"].map(lambda sites: [s for s in sites if s not in NOT_STREAMING])
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    for col in ["start_date", "end_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["studio_list"] = df["main_studios"].where(df["main_studios"].str.len() > 0, df["studios"])
    df["staff"] = df["main_staff"].map(_parse_staff)
    df["main_staff"] = df["main_staff"].map(_split)
    df["synopsis"] = df["synopsis"].map(_clean_synopsis)

    df["year"] = df["season_year"].fillna(df["start_date"].dt.year).astype("Int64")
    df["decade"] = ((df["year"] // 10 * 10).astype("string") + "s").fillna(UNKNOWN).astype(str)
    df["length"] = (
        pd.cut(df["episodes"], bins=LENGTH_BINS, labels=LENGTH_ORDER).cat.add_categories(UNKNOWN).fillna(UNKNOWN)
    ).astype(str)
    df["watch_hours"] = df["episodes"] * df["duration"] / 60

    # people that started the work on AniList; plan_to_watch is left out since they never watched it
    engaged = df[["watching", "completed", "on_hold", "dropped"]].sum(axis=1, min_count=1).replace(0, np.nan)
    df["completion_rate"] = df["completed"] / engaged
    df["drop_rate"] = df["dropped"] / engaged
    df["favorite_rate"] = df["favorites"] / df["popularity"].replace(0, np.nan) * 1000

    return df.reset_index(drop=True)


@st.cache_data(show_spinner="Loading your anime list...")
def load(path, modified_at):
    """modified_at is only part of the cache key, so the cache refreshes when the csv changes"""
    raw = pd.read_csv(path)
    missing = [col for col in RAW_COLUMNS if col not in raw.columns]
    if missing:
        return None, missing
    return prepare(raw), []


def load_or_stop(path):
    if not os.path.exists(path):
        st.error(f"`{path}` was not found. Run **Sync your csv** (option 1 in `main.sh`) to create it.",
                 icon=":material/error:")
        st.stop()

    df, missing = load(path, os.path.getmtime(path))
    if missing:
        st.error(
            f"`{path}` is missing the columns {', '.join(missing)}. It was probably created by an older version "
            "of the program, run **Sync your csv** (option 1 in `main.sh`) to rebuild it.",
            icon=":material/error:",
        )
        st.stop()
    if df.empty:
        st.info(f"`{path}` has no works yet. Add some with **Add work** or **Sync your csv**.",
                icon=":material/info:")
        st.stop()
    return df


def with_names(df, prefer_english):
    """add 'name', the title shown in charts. Repeated names get their format and year so charts don't merge them"""
    name = df["title"].fillna(df["english_title"]).fillna(UNKNOWN)
    if prefer_english:
        name = df["english_title"].fillna(name)

    repeated = name.duplicated(keep=False)
    name = name.where(~repeated, name + " (" + df["type"] + ", " + df["year"].astype("string").fillna("?") + ")")
    repeated = name.duplicated(keep=False)
    name = name.where(~repeated, name + " #" + df["anime_id"].astype(str))
    return df.assign(name=name)


def apply_filters(df, filters):
    """filters: categories {col: [values]}, lists {col: ([values], match_all)},
    ranges {col: (low, high, keep_unknown)}. Empty selections don't filter"""

    mask = pd.Series(True, index=df.index)

    for col, chosen in filters["categories"].items():
        if chosen:
            mask &= df[col].isin(chosen)

    for col, (chosen, match_all) in filters["lists"].items():
        if chosen:
            wanted = set(chosen)
            mask &= df[col].map(lambda values: wanted.issubset(values) if match_all else not wanted.isdisjoint(values))

    for col, (low, high, keep_unknown) in filters["ranges"].items():
        in_range = df[col].between(low, high).fillna(False).astype(bool)
        mask &= in_range | (df[col].isna() & keep_unknown)

    return df[mask]


def rows_by(df, col, keep):
    """one row per known value of col with the keep columns. List columns give one row per item,
    works where col is unknown or empty are dropped"""
    out = df[[col, *keep]]
    if col in LIST_LIKE:
        out = out.explode(col)
    out = out.dropna(subset=[col])
    return out[out[col] != UNKNOWN]


def counts(df, col):
    """how many works have each known value of col, most common first"""
    return rows_by(df, col, [])[col].value_counts()


def options(df, col):
    """sorted choices for a filter, Unknown last"""
    if col in LIST_LIKE:
        values = set(df[col].explode().dropna())
    else:
        values = set(df[col].dropna())

    order = {"season": SEASON_ORDER, "length": LENGTH_ORDER, "type": FORMAT_ORDER}.get(col)
    known = sorted(values - {UNKNOWN}, key=str.lower)
    if order:
        known = [v for v in order if v in values] + [v for v in known if v not in order]
    return known + ([UNKNOWN] if UNKNOWN in values else [])
