import streamlit as st
from dashboard import charts, data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Watch time", "Where did your hours go?",
        "Episodes and minutes behind your list: the long runners, the quick watches and whether the long ones "
        "were worth it.")

timed = df.dropna(subset=["watch_hours"])
if timed.empty:
    st.info("None of these works has both episodes and duration, so their watch time is unknown.")
    st.stop()

hours = timed["watch_hours"]
longest = timed.loc[hours.idxmax()]
top5_share = hours.nlargest(5).sum() / hours.sum() if hours.sum() else 0
ui.kpis([
    ("Total time", f"{hours.sum() / 24:,.1f} days", f"{hours.sum():,.0f} hours"),
    ("Per work", f"{hours.mean():,.1f} h", f"Median {hours.median():,.1f} hours"),
    ("Episodes", ui.text(df["episodes"].sum(min_count=1), ",.0f"),
     f"Median {ui.text(df['episodes'].median(), ',.0f')} per work"),
    ("Episode length", f"{ui.text(df['duration'].median(), ',.0f')} min", "Median minutes per episode"),
    ("Longest work", longest["name"], f"{longest['watch_hours']:,.0f} hours"),
    ("Top 5 share", f"{top5_share:.0%}", "Of your time went to your 5 longest works"),
    ("Binge-able", f"{(hours <= 6).mean():.0%}", "Works you can finish in 6 hours or less"),
    ("Long runners", f"{int((df['episodes'] > 52).sum()):,}", "Works with more than 52 episodes"),
])
ui.missing_note(df, "watch_hours", "watch time (episodes or duration)")

left, right = st.columns(2, gap="large")
with left:
    ui.section("Biggest time sinks")
    top_n = ui.top_n("Works shown", len(timed), 15, "wt_top")
    charts.show(charts.ranked_bar(timed.nlargest(top_n, "watch_hours"), "name", "watch_hours", {
        "val_title": "Hours", "cat_title": "Title",
        "tooltip": [("episodes:Q", "Episodes", ",.0f"), ("score:Q", "Score", ".0f")]}))
with right:
    ui.section("Episodes by format", "Each box is the middle 50% of works.")
    episodes = df.dropna(subset=["episodes"])
    episodes = episodes[episodes["type"] != data.UNKNOWN]
    charts.show(charts.boxplot(episodes, "type", "episodes", {"val_title": "Episodes (log scale)", "scale": "log"}))

ui.section("Were the long ones worth it?", "Hours against score, dashed line is the trend. Zoom with the mouse wheel.")
scored = timed.dropna(subset=["score"])
if scored.empty:
    st.info("No scored works with a known watch time.")
else:
    charts.show(charts.scatter(scored, "watch_hours", "score", {
        "x_title": "Hours (log scale)", "y_title": "Score", "x_scale": "log", "color": "type",
        "palette": data.FORMAT_COLORS, "trend": True,
        "tooltip": [("name:N", "Title", None), ("episodes:Q", "Episodes", ",.0f"),
                    ("watch_hours:Q", "Hours", ",.1f"), ("score:Q", "Score", ".0f")]}))
