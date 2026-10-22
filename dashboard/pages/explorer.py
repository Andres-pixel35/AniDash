import streamlit as st
from dashboard import data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Explorer", "Every work on your list",
        "Pick the columns you care about, sort by clicking a header and select a row to see the whole work.")

DEFAULT = ["title", "type", "year", "season", "episodes", "watch_hours", "score", "genres", "studio_list", "source"]
event, view = ui.column_table(df, DEFAULT, "ex")

left, right = st.columns([3, 1])
left.caption(f"{len(view):,} works · missing values show as {data.UNKNOWN}. Select a row for its details.")
right.download_button("Download CSV", view.to_csv(index=False, na_rep=data.UNKNOWN), "anime_list.csv", "text/csv",
                      icon=":material/download:", width="stretch")

if not event.selection.rows:
    st.stop()

ui.work_card(df.iloc[event.selection.rows[0]])
