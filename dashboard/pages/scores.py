import streamlit as st
from dashboard import charts, data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Scores", "How good is your list?",
        "AniList scores (0-100) of the works you watched: their spread, what scores higher and where your "
        "favourites stand.")

scored = df.dropna(subset=["score"])
if scored.empty:
    st.info("None of these works has a score yet.")
    st.stop()

score = scored["score"]
best, worst = scored.loc[score.idxmax()], scored.loc[score.idxmin()]
ui.kpis([
    ("Average score", f"{score.mean():.1f}", f"Median {score.median():.0f}"),
    ("Spread", f"±{score.std():.1f}" if len(score) > 1 else "±0", "Standard deviation"),
    ("Excellent works", f"{(score >= 80).mean():.0%}", f"{int((score >= 80).sum()):,} works scored 80 or more"),
    ("Below 60", f"{(score < 60).mean():.0%}", f"{int((score < 60).sum()):,} works"),
    ("Best scored", best["name"], f"Score {best['score']:.0f}"),
    ("Worst scored", worst["name"], f"Score {worst['score']:.0f}"),
    ("Scored works", f"{len(scored):,}", f"{len(df) - len(scored):,} without a score"),
    ("Average users' mean", ui.text(scored["mean_score"].mean(), ".1f"), "AniList mean user score"),
], per_row=4)

left, right = st.columns([3, 2], gap="large")
with left:
    ui.section("Distribution")
    charts.show(charts.histogram(score, {"title": "Score", "bins": 25}))
    ui.missing_note(df, "score", "score")
with right:
    ui.section("Score bands")
    bands = (score // 10 * 10).astype(int).map(lambda b: f"{b}-{b + 9}").value_counts().sort_index()
    charts.show(charts.columns(bands.rename_axis("band").reset_index(name="works"), "band", "works", {
        "y_title": "Works", "x_title": "Score band"}))

ui.section("What scores higher?", "Each box holds the middle 50% of works, the line inside is the median. "
                                  "Dots are outliers. The number next to each label is how many works it has.")
DIMENSIONS = {"Format": "type", "Source material": "source", "Season": "season", "Decade": "decade",
              "Genre": "genres", "Length": "length", "Studio": "studio_list"}
controls = st.columns([3, 1])
dimension = controls[0].segmented_control("Compare by", list(DIMENSIONS), default="Format", key="sc_dim") or "Format"
col = DIMENSIONS[dimension]
groups = data.rows_by(scored, col, ["score"])
if groups[col].nunique() > 5:
    top_n = controls[1].number_input("Groups shown", min_value=3, max_value=30, value=12, key="sc_top")
    groups = groups[groups[col].isin(groups[col].value_counts().head(top_n).index)]
charts.show(charts.boxplot(groups, col, "score", {"val_title": "Score"}))

ui.section("Average score by genre")
min_works = st.slider("Minimum works per genre", 1, 20, 3, key="sc_min_genre")
genre_scores = data.rows_by(scored, "genres", ["score"]).groupby("genres")["score"].agg(["mean", "size"])
genre_scores = genre_scores[genre_scores["size"] >= min_works].sort_values("mean", ascending=False)
if genre_scores.empty:
    st.info("No genre has that many works, lower the minimum.")
else:
    charts.show(charts.ranked_bar(genre_scores.reset_index(), "genres", "mean", {
        "val_title": "Average score", "cat_title": "Genre", "format": ".1f",
        "tooltip": [("size:Q", "Works", ",.0f")]}))

ui.section("Score vs popularity", "Top left: well rated but little known. Use the mouse wheel to zoom.")
charts.show(charts.scatter(scored, "popularity", "score", {
    "x_title": "Popularity (AniList users, log scale)", "y_title": "Score", "x_scale": "log",
    "color": "type", "palette": data.FORMAT_COLORS, "size": "favorites", "trend": True, "height": 480,
    "tooltip": [("name:N", "Title", None), ("type:N", "Format", None), ("score:Q", "Score", ".0f"),
                ("popularity:Q", "Users", ",.0f"), ("favorites:Q", "Favorites", ",.0f")]}))

columns = {"name": "Title", "type": "Format", "year": "Year", "score": "Score", "popularity": "Users"}
formats = {"score": "{:.0f}", "popularity": "{:,.0f}"}
left, right = st.columns(2, gap="large")
with left:
    ui.section("Top 10")
    ui.table(scored.nlargest(10, "score"), columns, formats)
with right:
    ui.section("Bottom 10")
    ui.table(scored.nsmallest(10, "score"), columns, formats)
