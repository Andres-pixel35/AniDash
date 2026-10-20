import streamlit as st
from dashboard import charts, data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Community", "How does your list compare with everyone else?",
        "AniList audience numbers for the works you watched: how mainstream your taste is, which works people "
        "drop and which ones they love.")

popularity = df["popularity"].dropna()
niche = (popularity < 50_000).mean() if len(popularity) else None
loved = df.dropna(subset=["favorite_rate"])
most_loved = loved.loc[loved["favorite_rate"].idxmax()] if not loved.empty else None
ui.kpis([
    ("Median popularity", ui.text(popularity.median(), ",.0f"), "AniList users per work on your list"),
    ("Niche picks", f"{niche:.0%}" if niche is not None else data.UNKNOWN, "Works with fewer than 50k users"),
    ("Completion rate", f"{df['completion_rate'].mean():.0%}" if df["completion_rate"].notna().any() else data.UNKNOWN,
     "Average share of viewers who finish"),
    ("Drop rate", f"{df['drop_rate'].mean():.0%}" if df["drop_rate"].notna().any() else data.UNKNOWN,
     "Average share of viewers who drop"),
    ("Total favorites", ui.text(df["favorites"].sum(min_count=1), ",.0f"), "Times users favorited these works"),
    ("Most loved", most_loved["name"] if most_loved is not None else data.UNKNOWN,
     f"{most_loved['favorite_rate']:.0f} favorites per 1k users" if most_loved is not None else "No data"),
    ("Most popular", df.loc[popularity.idxmax(), "name"] if len(popularity) else data.UNKNOWN,
     f"{popularity.max():,.0f} users" if len(popularity) else "No data"),
    ("Least known", df.loc[popularity.idxmin(), "name"] if len(popularity) else data.UNKNOWN,
     f"{popularity.min():,.0f} users" if len(popularity) else "No data"),
])

ui.section("Popularity vs love", "Users who have the work on their list against users who favorited it. "
                                 "Above the trend: loved more than its popularity suggests.")
# log scales can't show 0, works nobody favorited are left out
audience = df[(df["popularity"] > 0) & (df["favorites"] > 0)]
charts.show(charts.scatter(audience, "popularity", "favorites", {
    "x_title": "Popularity (log scale)", "y_title": "Favorites (log scale)", "x_scale": "log", "y_scale": "log",
    "color": "type", "palette": data.FORMAT_COLORS, "trend": True, "height": 460,
    "tooltip": [("name:N", "Title", None), ("popularity:Q", "Users", ",.0f"), ("favorites:Q", "Favorites", ",.0f"),
                ("favorite_rate:Q", "Favorites per 1k users", ".1f"), ("score:Q", "Score", ".0f")]}))

left, right = st.columns(2, gap="large")
with left:
    ui.section("Most dropped by others", "Share of viewers who dropped the work.")
    dropped = df.dropna(subset=["drop_rate"]).nlargest(12, "drop_rate")
    charts.show(charts.ranked_bar(dropped, "name", "drop_rate", {
        "val_title": "Drop rate", "cat_title": "Title", "format": ".0%",
        "tooltip": [("dropped:Q", "Dropped", ",.0f"), ("score:Q", "Score", ".0f")]}))
with right:
    ui.section("Most loved", "Favorites for every 1,000 users who have the work.")
    charts.show(charts.ranked_bar(loved.nlargest(12, "favorite_rate"), "name", "favorite_rate", {
        "val_title": "Favorites per 1k users", "cat_title": "Title", "format": ".0f",
        "tooltip": [("favorites:Q", "Favorites", ",.0f"), ("popularity:Q", "Users", ",.0f")]}))

ui.section("Completion rate by format")
rates = df.dropna(subset=["completion_rate"])
rates = rates[rates["type"] != data.UNKNOWN].assign(completion=lambda d: d["completion_rate"] * 100)
charts.show(charts.boxplot(rates, "type", "completion", {"val_title": "Viewers who finish (%)"}))

ui.section("Hidden gems on your list", "Works scored in your top quarter with the fewest AniList users.")
scored = df.dropna(subset=["score"])
if scored.empty:
    st.info("No scored works to look for gems.")
else:
    gems = scored[scored["score"] >= scored["score"].quantile(0.75)].nsmallest(10, "popularity")
    ui.table(gems, {"name": "Title", "type": "Format", "year": "Year", "score": "Score", "popularity": "Users",
                    "favorite_rate": "Favorites per 1k users"},
             {"score": "{:.0f}", "popularity": "{:,.0f}", "favorite_rate": "{:.1f}"})
