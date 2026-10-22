import json
from pathlib import Path
import pandas as pd
import streamlit as st
from dashboard import data, filters
from dashboard.components import inject_css
from src.pipeline.helpers import season_offset

CONFIG = json.loads(Path("config.json").read_text())

st.set_page_config(page_title=f"{CONFIG['user_name']}'s Anime Dashboard", page_icon=":material/live_tv:", layout="wide")
inject_css()

PAGES = "dashboard/pages/"
predictor = st.Page(PAGES + "predictor.py", title="Score predictor", icon=":material/model_training:")
explorer = st.Page(PAGES + "explorer.py", title="Explorer", icon=":material/table_view:")
airing = st.Page(PAGES + "airing.py", title="Airing", icon=":material/podcasts:")
page = st.navigation([
    st.Page(PAGES + "overview.py", title="Overview", icon=":material/space_dashboard:", default=True),
    st.Page(PAGES + "timeline.py", title="Timeline", icon=":material/timeline:"),
    st.Page(PAGES + "scores.py", title="Scores", icon=":material/star:"),
    st.Page(PAGES + "content.py", title="Genres & Studios", icon=":material/category:"),
    st.Page(PAGES + "watch_time.py", title="Watch time", icon=":material/schedule:"),
    st.Page(PAGES + "community.py", title="Community", icon=":material/groups:"),
    explorer,
    airing,
    predictor,
], position="top")

# the predictor doesn't use the user's list, so it neither needs final.csv nor shows the filters
if page.url_path != predictor.url_path:
    if page.url_path == airing.url_path:
        # the airing csv also holds works refetched once they stopped airing, those are left out
        df = data.load_or_stop(CONFIG["path_modified_airing"])
        df = df[df["status"].isin(["Releasing", "Not Yet Released"])]
        # anime.csv adds the works of this and next season that already finished, like a movie released this season
        history = data.load_or_stop(CONFIG["path_historical_csv"])
        df = pd.concat([df, *[history[(history["season"] == s.title()) & (history["season_year"] == y)]
                              for s, y in (season_offset(0), season_offset(1))]]).drop_duplicates("anime_id")
        chosen = filters.render_airing_sidebar(df)
    else:
        df = data.load_or_stop(CONFIG["path_final_csv"])
        chosen = filters.render_sidebar(df, english=page.url_path != explorer.url_path)
    df = data.with_names(df, st.session_state.get("f_english", False))
    filtered = data.apply_filters(df, chosen)
    st.session_state["full"] = df
    st.session_state["filtered"] = filtered
    active = filters.active_count(chosen, df)
    st.sidebar.caption(f"Showing **{len(filtered):,}** of {len(df):,} works"
                       + (f" · {active} active filter{'s' if active != 1 else ''}" if active else ""))

page.run()
