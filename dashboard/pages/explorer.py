import pandas as pd
import streamlit as st
from dashboard import data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Explorer", "Every work on your list",
        "Pick the columns you care about, sort by clicking a header and select a row to see the whole work.")

DEFAULT = ["title", "english_title", "type", "year", "season", "episodes", "watch_hours", "score", "genres",
           "studio_list", "source"]
OPTIONAL = [col for col in data.LABELS if col not in ("name", "synopsis")]
FORMATS = {
    "episodes": "{:,.0f}", "duration": "{:,.0f}", "watch_hours": "{:,.1f}", "score": "{:.0f}", "mean_score": "{:.0f}",
    "popularity": "{:,.0f}", "favorites": "{:,.0f}", "favorite_rate": "{:.1f}", "watching": "{:,.0f}",
    "completed": "{:,.0f}", "on_hold": "{:,.0f}", "dropped": "{:,.0f}", "plan_to_watch": "{:,.0f}",
    "completion_rate": "{:.0%}", "drop_rate": "{:.0%}",
}

columns = st.multiselect("Columns", OPTIONAL, default=DEFAULT, format_func=data.LABELS.get, key="ex_columns")
if not columns:
    st.info("Choose at least one column.")
    st.stop()

view = df[columns].copy()
for col in columns:
    if col in data.LIST_LIKE:
        view[col] = view[col].map(lambda values: ", ".join(values) if values else None)
    elif pd.api.types.is_datetime64_any_dtype(view[col]):
        view[col] = view[col].dt.strftime("%Y-%m-%d")
view = view.rename(columns=data.LABELS)

# Styler only changes what is displayed, sorting a column still uses the real numbers
styler = view.style.format(na_rep=data.UNKNOWN).format(
    {data.LABELS[col]: fmt for col, fmt in FORMATS.items() if col in columns}, na_rep=data.UNKNOWN)
link = {data.LABELS["site_url"]: st.column_config.LinkColumn(data.LABELS["site_url"], display_text="Open")}
event = st.dataframe(styler, hide_index=True, width="stretch", height=480, on_select="rerun",
                     selection_mode="single-row", key=ui.selection_key("ex_table", df), column_config=link)

left, right = st.columns([3, 1])
left.caption(f"{len(view):,} works · missing values show as {data.UNKNOWN}. Select a row for its details.")
right.download_button("Download CSV", view.to_csv(index=False, na_rep=data.UNKNOWN), "anime_list.csv", "text/csv",
                      icon=":material/download:", width="stretch")

if not event.selection.rows:
    st.stop()

ui.work_card(df.iloc[event.selection.rows[0]])
