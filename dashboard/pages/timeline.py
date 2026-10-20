import pandas as pd
import streamlit as st
from dashboard import charts, data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Timeline", "When were your anime made?",
        "How your list spreads across the years, which eras you favour and whether older works scored better.")

dated = df.dropna(subset=["year"])
if dated.empty:
    st.info("None of these works has a known release year.")
    st.stop()

top_decade = data.counts(df, "decade")
per_year = dated["year"].value_counts()
oldest = dated.sort_values(["year", "start_date"], na_position="last").iloc[0]
newest = dated.sort_values(["year", "start_date"], na_position="first").iloc[-1]
ui.kpis([
    ("Oldest release", str(oldest["year"]), oldest["name"]),
    ("Newest release", str(newest["year"]), newest["name"]),
    ("Favourite decade", top_decade.index[0], f"{top_decade.iloc[0] / len(df):.0%} of your list"),
    ("Median release year", f"{dated['year'].median():.0f}", f"{ui.plural(per_year.size, 'year')} with releases"),
])

controls = st.columns([1, 1, 2])
period = controls[0].segmented_control("Group by", ["Year", "Decade"], default="Year", key="tl_period") or "Year"
split = controls[1].selectbox("Colour by", ["Format", "Season", "Source material", "Length"], key="tl_split")
period_col = "decade" if period == "Decade" else "year"
split_col = {"Format": "type", "Season": "season", "Source material": "source", "Length": "length"}[split]
period_data = dated if period_col == "year" else df[df["decade"] != data.UNKNOWN]

ui.section("Works released per period")
released = period_data.groupby([period_col, split_col]).size().reset_index(name="value")
charts.show(charts.stacked_columns(released, period_col, split_col, {
    "y_title": "Works", "color_title": split, "x_title": period,
    "color_sort": data.options(df, split_col), "palette": data.FORMAT_COLORS if split_col == "type" else None}))
ui.missing_note(df, "year", "release year")

left, right = st.columns(2, gap="large")
with left:
    ui.section("Score through time", "Line: average score. Band: middle 50% of works.")
    scores = period_data.dropna(subset=["score"]).groupby(period_col)["score"]
    trend = pd.DataFrame({"mean": scores.mean(), "q1": scores.quantile(0.25), "q3": scores.quantile(0.75),
                          "n": scores.size()}).reset_index()
    if trend.empty:
        st.info("No scored works to show.")
    else:
        charts.show(charts.trend_band(trend, period_col, {"y_title": "Score", "x_title": period}))
with right:
    ui.section("Hours watched per period", "How much of your time each era took.")
    hours = period_data.groupby(period_col)["watch_hours"].sum(min_count=1).dropna().reset_index(name="hours")
    if hours.empty:
        st.info("No length data to show.")
    else:
        charts.show(charts.columns(hours, period_col, "hours", {"y_title": "Hours", "x_title": period}))
    ui.missing_note(period_data, "watch_hours", "length")

ui.section("Season calendar", "Works per season and year. Brighter means more works.")
calendar = dated[dated["season"] != data.UNKNOWN].groupby(["year", "season"]).size().reset_index(name="value")
if calendar.empty:
    st.info("No seasons to show.")
else:
    charts.show(charts.heatmap(calendar, "year", "season", {
        "value_title": "Works", "y_sort": data.SEASON_ORDER, "x_title": "Year", "y_title": "Season", "height": 240}))

columns = {"name": "Title", "type": "Format", "start_date": "Start date", "score": "Score"}
formats = {"start_date": lambda d: f"{d:%Y-%m-%d}", "score": "{:.0f}"}
left, right = st.columns(2, gap="large")
with left:
    ui.section("Oldest works")
    ui.table(df.sort_values("start_date", na_position="last").head(10), columns, formats)
with right:
    ui.section("Newest works")
    ui.table(df.sort_values("start_date", ascending=False, na_position="last").head(10), columns, formats)

airing = df[df["status"].isin(["Releasing", "Not Yet Released"])]
if not airing.empty:
    ui.section("Still airing", "Works on your list that haven't finished.")
    ui.table(airing, {"name": "Title", "status": "Status", "episodes": "Total episodes", "start_date": "Start date",
                      "score": "Score"}, {"episodes": "{:.0f}", "start_date": lambda d: f"{d:%Y-%m-%d}",
                                          "score": "{:.0f}"})
