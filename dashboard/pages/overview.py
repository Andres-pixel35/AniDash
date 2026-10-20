import json
from pathlib import Path
import pandas as pd
import streamlit as st
from dashboard import charts, data
from dashboard import components as ui

CONFIG = json.loads(Path("config.json").read_text())

df = ui.page_data()
total = len(st.session_state["full"])

years = df["year"].dropna()
span = f"{years.min()}-{years.max()}" if len(years) else data.UNKNOWN
chips = [f"Filtered from {total:,}"] if len(df) < total else []
ui.hero("Your anime journey", f"{CONFIG['user_name']}'s Anime Dashboard",
        "Everything you have watched, measured: how much, how long, what you like and how it compares "
        "with the AniList community.", chips)

# --- headline numbers ---
formats = data.counts(df, "type")
format_sub = " · ".join(f"{n} {name}" for name, n in formats.head(3).items()) or "Format unknown"
episodes = df["episodes"].sum(min_count=1)
hours = df["watch_hours"].sum(min_count=1)
scored = df["score"].dropna()
studios = data.counts(df, "studio_list")

ui.kpis([
    ("Works watched", f"{len(df):,}", format_sub),
    ("Episodes", ui.text(episodes, ",.0f"), f"About {ui.text(df['episodes'].mean(), '.0f')} per work"),
    ("Time watched", f"{ui.text(hours / 24, ',.1f')} days" if pd.notna(hours) else data.UNKNOWN,
     f"{ui.text(hours, ',.0f')} hours in front of the screen"),
    ("Average score", ui.text(scored.mean(), ".1f"),
     f"Median {ui.text(scored.median(), '.0f')} · {len(scored):,} of {len(df):,} scored"),
    ("Release span", span, ui.plural(years.nunique(), "distinct year")),
    ("Studios", f"{len(studios):,}", f"Most watched: {studios.index[0]}" if len(studios) else "No studio data"),
    ("Genres explored", f"{len(data.counts(df, 'genres')):,}", f"{len(data.counts(df, 'tags')):,} different tags"),
    ("Still airing", f"{int((df['status'] == 'Releasing').sum()):,}",
     f"{int((df['status'] == 'Finished').sum()):,} finished works"),
])


def favourite(col, unit):
    """(value, sub) for the most common value of col"""
    values = data.counts(df, col)
    if values.empty:
        return data.UNKNOWN, "No data"
    return values.index[0], f"{values.iloc[0]:,} {unit} · {values.iloc[0] / len(df):.0%} of your list"


ui.section("Your taste", "The most common traits of the works you watched.")
year_values = data.counts(df, "year")
ui.kpis([
    ("Top genre", *favourite("genres", "works")),
    ("Top tag", *favourite("tags", "works")),
    ("Top source", *favourite("source", "works")),
    ("Top studio", *favourite("studio_list", "works")),
    ("Favourite format", *favourite("type", "works")),
    ("Favourite season", *favourite("season", "works")),
    ("Busiest year", str(year_values.index[0]) if len(year_values) else data.UNKNOWN,
     f"{year_values.iloc[0]:,} works released that year" if len(year_values) else "No data"),
    ("Typical length", *favourite("length", "works")),
])

# --- charts ---
left, right = st.columns([3, 2], gap="large")
with left:
    ui.section("Works by release year")
    per_year = df.dropna(subset=["year"]).groupby(["year", "type"]).size().reset_index(name="value")
    if per_year.empty:
        st.info("No release years to show.")
    else:
        charts.show(charts.stacked_columns(per_year, "year", "type", {
            "y_title": "Works", "color_title": "Format", "x_title": "Year", "palette": data.FORMAT_COLORS}))
    ui.missing_note(df, "year", "release year")
with right:
    ui.section("Formats")
    shares = formats.rename_axis("type").reset_index(name="works")
    shares["share"] = shares["works"] / shares["works"].sum()
    charts.show(charts.ranked_bar(shares, "type", "share", {
        "val_title": "Share of your list", "height": 320, "cat_title": "Format", "format": ".0%",
        "tooltip": [("works:Q", "Works", ",.0f")]}))

left, right = st.columns(2, gap="large")
with left:
    ui.section("Top 10 genres")
    genres = data.counts(df, "genres").head(10).rename_axis("genre").reset_index(name="works")
    genres["share"] = genres["works"] / len(df)
    charts.show(charts.ranked_bar(genres, "genre", "works", {
        "val_title": "Works", "cat_title": "Genre", "tooltip": [("share:Q", "Share of your list", ".0%")]}))
with right:
    ui.section("Score distribution")
    if scored.empty:
        st.info("None of these works has a score.")
    else:
        charts.show(charts.histogram(scored, {"title": "Score", "bins": 20}))
    ui.missing_note(df, "score", "score")

# --- spotlight ---
ui.section("Spotlight", "Standouts of your list.")


def pick(frame, col, largest=True):
    frame = frame.dropna(subset=[col])
    if frame.empty:
        return None
    return frame.nlargest(1, col).iloc[0] if largest else frame.nsmallest(1, col).iloc[0]


top_scored = pick(df, "score")
most_popular = pick(df, "popularity")
time_sink = pick(df, "watch_hours")
oldest = pick(df, "start_date", largest=False)
good = df[df["score"] >= scored.quantile(0.75)] if len(scored) else df.iloc[0:0]
gem = pick(good, "popularity", largest=False)

cards = []
for label, row, sub in [
    ("Highest rated", top_scored, lambda r: f"Score {ui.text(r['score'], ',.0f')}"),
    ("Most popular", most_popular, lambda r: f"{ui.text(r['popularity'], ',.0f')} AniList users"),
    ("Biggest time sink", time_sink, lambda r: f"{ui.text(r['watch_hours'], ',.1f')} hours"),
    ("Hidden gem", gem,
     lambda r: f"Score {ui.text(r['score'], ',.0f')}, only {ui.text(r['popularity'], ',.0f')} users"),
    ("Oldest", oldest, lambda r: f"Released {r['start_date']:%B %Y}"),
]:
    cards.append((label, row["name"], sub(row)) if row is not None else (label, data.UNKNOWN, "No data"))
ui.kpis(cards, per_row=5, titles=True)
