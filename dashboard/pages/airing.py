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

COLUMNS = {
    "name": "Title", "type": "Format", "status": "Airing status", "episodes": "Episodes", "start_date": "Start date",
    "studio_list": "Studios", "genres": "Genres", "score": "Score", "popularity": "Popularity",
    "streaming_sites": "Streaming on", "site_url": "AniList page",
}
shown = shown.sort_values("popularity", ascending=False)
event = st.dataframe(
    shown[list(COLUMNS)], hide_index=True, width="stretch", height=560, on_select="rerun",
    selection_mode="single-row", key=ui.selection_key("air_table", shown),
    column_config=COLUMNS | {
        "start_date": st.column_config.DateColumn("Start date", format="YYYY-MM-DD"),
        "site_url": st.column_config.LinkColumn("AniList page", display_text="Open"),
    },
)
st.caption(f"{ui.plural(len(shown), 'work')} · sorted by popularity, click a header to sort by it. "
           "Select a row for its details.")

if event.selection.rows:
    ui.work_card(shown.iloc[event.selection.rows[0]])
