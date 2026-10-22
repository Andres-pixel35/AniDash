import streamlit as st
from dashboard import components as ui
from src.pipeline.helpers import season_offset

df = ui.page_data()
ui.hero("Airing", "What's on air", "Every work releasing right now, or what this and next season bring.")

seasons = {"This season": season_offset(0), "Next season": season_offset(1)}
view = st.segmented_control(
    "Show", ["Airing now", *seasons], default="Airing now", required=True, key="air_view",
    format_func=lambda v: f"{v} · {seasons[v][0].title()} {seasons[v][1]}" if v in seasons else v,
)

if view == "Airing now":
    shown = df[df["status"] == "Releasing"]
else:
    season, year = seasons[view]
    shown = df[(df["season"] == season.title()) & (df["season_year"] == year)]

if shown.empty:
    st.info("No works match this view and the current filters.", icon=":material/info:")
    st.stop()

DEFAULT = ["title", "type", "status", "episodes", "start_date", "studio_list", "genres", "score", "popularity",
           "streaming_sites", "site_url"]
shown = shown.sort_values("popularity", ascending=False)
event, _ = ui.column_table(shown, DEFAULT, "air", height=560)
st.caption(f"{ui.plural(len(shown), 'work')} · sorted by popularity, click a header to sort by it. "
           "Select a row for its details.")

if event.selection.rows:
    ui.work_card(shown.iloc[event.selection.rows[0]])
