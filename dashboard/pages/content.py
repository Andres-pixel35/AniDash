import pandas as pd
import streamlit as st
from dashboard import charts, data
from dashboard import components as ui

df = ui.page_data()
ui.hero("Genres & Studios", "What do you watch?",
        "Genres, tags, source material, studios and the people behind the works on your list.")


def summary(col, label):
    """works, share, average score and hours per value of col"""
    rows = data.rows_by(df, col, ["score", "watch_hours"])
    out = rows.groupby(col).agg(works=("score", "size"), avg_score=("score", "mean"),
                                hours=("watch_hours", lambda h: h.sum(min_count=1)))
    out["share"] = out["works"] / len(df)
    return out.sort_values("works", ascending=False).rename_axis(label).reset_index()


SUMMARY_COLUMNS = {"works": "Works", "share": "Share of list", "avg_score": "Average score", "hours": "Hours"}
SUMMARY_FORMATS = {"works": "{:,.0f}", "share": "{:.0%}", "avg_score": "{:.1f}", "hours": "{:,.0f}"}

# a segmented control instead of st.tabs: tabs keep the open tab in the browser, and a widget rerun inside
# one could jump back to the first tab or show every tab's content at once
SECTIONS = {"Genres": ":material/theater_comedy:", "Tags": ":material/sell:", "Source material": ":material/menu_book:",
            "Studios": ":material/movie:", "People": ":material/person:"}
section = st.segmented_control("Section", list(SECTIONS), default="Genres", key="ct_section",
                               format_func=lambda name: f"{SECTIONS[name]} {name}",
                               label_visibility="collapsed") or "Genres"

if section == "Genres":
    genres = summary("genres", "Genre")
    left, right = st.columns(2, gap="large")
    with left:
        ui.section("How often each genre appears")
        charts.show(charts.ranked_bar(genres, "Genre", "works", {
            "val_title": "Works", "cat_title": "Genre",
            "tooltip": [("share:Q", "Share of list", ".0%"), ("avg_score:Q", "Average score", ".1f")]}))
        ui.missing_note(df, "genres", "genres")
    with right:
        ui.section("Genre mix by decade", "Share of each decade's works that has the genre.")
        by_decade = data.rows_by(df[df["decade"] != data.UNKNOWN], "genres", ["decade"])
        by_decade = by_decade[by_decade["genres"].isin(genres["Genre"].head(12))]
        per_decade = df[df["decade"] != data.UNKNOWN]["decade"].value_counts()
        # unstack/stack fills the decades where a genre never appears with 0 instead of leaving a hole
        mix = by_decade.groupby(["decade", "genres"]).size().unstack(fill_value=0).stack().reset_index(name="works")
        mix["value"] = mix["works"] / mix["decade"].map(per_decade)
        if mix.empty:
            st.info("No decades to compare.")
        else:
            charts.show(charts.heatmap(mix, "decade", "genres", {
                "value_title": "Share of the decade", "format": ".0%", "y_sort": genres["Genre"].head(12).tolist(),
                "x_title": "Decade", "y_title": "Genre"}))

    ui.section("Genres that go together", "How many works share each pair of genres.")
    top = genres["Genre"].head(12).tolist()
    pairs = df["genres"].map(lambda g: [x for x in g if x in top])
    matrix = pd.DataFrame(0, index=top, columns=top)
    for gs in pairs:
        for a in gs:
            for b in gs:
                if a != b:
                    matrix.loc[a, b] += 1
    long = matrix.rename_axis("genre_a").reset_index().melt("genre_a", var_name="genre_b", value_name="value")
    charts.show(charts.heatmap(long, "genre_b", "genre_a", {
        "value_title": "Works together", "x_sort": top, "y_sort": top, "x_title": "Together with", "y_title": "Genre",
        "height": 460, "x_label_angle": -90}))
    ui.table(genres, {"Genre": "Genre", **SUMMARY_COLUMNS}, SUMMARY_FORMATS)

if section == "Tags":
    tags = summary("tags", "Tag")
    if tags.empty:
        st.info("None of these works has tags.")
    else:
        top_n = ui.top_n("Tags shown", len(tags), 20, "ct_tags")
        left, right = st.columns(2, gap="large")
        with left:
            ui.section("Most common tags")
            charts.show(charts.ranked_bar(tags.head(top_n), "Tag", "works", {
                "val_title": "Works", "cat_title": "Tag", "tooltip": [("share:Q", "Share of list", ".0%")]}))
        with right:
            ui.section("Best scored tags", "Tags in at least 3 works, by average score.")
            best = tags[(tags["works"] >= 3) & tags["avg_score"].notna()].nlargest(top_n, "avg_score")
            if best.empty:
                st.info("No tag appears in 3 or more scored works.")
            else:
                charts.show(charts.ranked_bar(best, "Tag", "avg_score", {
                    "val_title": "Average score", "cat_title": "Tag", "format": ".1f",
                    "tooltip": [("works:Q", "Works", ",.0f")]}))
        ui.table(tags, {"Tag": "Tag", **SUMMARY_COLUMNS}, SUMMARY_FORMATS)

if section == "Source material":
    sources = summary("source", "Source")
    left, right = st.columns(2, gap="large")
    with left:
        ui.section("Where the stories come from")
        charts.show(charts.ranked_bar(sources, "Source", "share", {
            "val_title": "Share of your list", "height": 320, "cat_title": "Source", "format": ".0%",
            "tooltip": [("works:Q", "Works", ",.0f")]}))
        ui.missing_note(df, "source", "source")
    with right:
        ui.section("Score by source")
        scored = df[(df["source"] != data.UNKNOWN) & df["score"].notna()]
        if scored.empty:
            st.info("No scored works with a known source.")
        else:
            charts.show(charts.boxplot(scored, "source", "score", {"val_title": "Score"}))
    ui.table(sources, {"Source": "Source", **SUMMARY_COLUMNS}, SUMMARY_FORMATS)

if section == "Studios":
    studios = summary("studio_list", "Studio")
    if studios.empty:
        st.info("None of these works has studio data.")
    else:
        top_n = ui.top_n("Studios shown", len(studios), 15, "ct_studios")
        left, right = st.columns(2, gap="large")
        with left:
            ui.section("Studios you watched the most", "Bar end: average score of their works on your list.")
            charts.show(charts.ranked_bar(studios.head(top_n), "Studio", "works", {
                "val_title": "Works", "cat_title": "Studio", "label": ("avg_score", ".1f"),
                "tooltip": [("avg_score:Q", "Average score", ".1f"), ("hours:Q", "Hours", ",.0f")]}))
        with right:
            ui.section("Hours given to each studio")
            charts.show(charts.ranked_bar(studios.dropna(subset=["hours"]).nlargest(top_n, "hours"), "Studio",
                                          "hours", {"val_title": "Hours", "cat_title": "Studio",
                                                    "tooltip": [("works:Q", "Works", ",.0f")]}))
        ui.section("Studio quality vs quantity", "Studios with more works to the right, better scored ones higher.")
        charts.show(charts.scatter(studios.dropna(subset=["avg_score"]), "works", "avg_score", {
            "x_title": "Works on your list", "y_title": "Average score", "x_scale": "log", "size": "hours",
            "height": 380, "tooltip": [("Studio:N", "Studio", None), ("works:Q", "Works", ",.0f"),
                                       ("avg_score:Q", "Average score", ".1f"), ("hours:Q", "Hours", ",.0f")]}))
        ui.table(studios, {"Studio": "Studio", **SUMMARY_COLUMNS}, SUMMARY_FORMATS)

if section == "People":
    staff = df[["name", "score", "staff"]].explode("staff").dropna(subset=["staff"])
    if staff.empty:
        st.info("None of these works has staff data.")
    else:
        staff["person"] = staff["staff"].str[0]
        staff["role"] = staff["staff"].str[1]
        roles = staff["role"].value_counts()
        role = st.selectbox("Role", roles.index.tolist(), key="ct_role",
                            index=roles.index.tolist().index("Director") if "Director" in roles.index else 0)
        people = staff[staff["role"] == role].groupby("person").agg(
            works=("name", "nunique"), avg_score=("score", "mean"),
            titles=("name", lambda names: ", ".join(sorted(set(names))))).sort_values("works", ascending=False)
        ui.section(f"Top people as {role}", "AniList lists up to 10 key staff per work, so smaller roles are partial.")
        charts.show(charts.ranked_bar(people.head(15).rename_axis("Person").reset_index(), "Person", "works", {
            "val_title": "Works", "cat_title": "Person", "label": ("avg_score", ".1f"),
            "tooltip": [("avg_score:Q", "Average score", ".1f"), ("titles:N", "Works", None)]}))
        ui.table(people.rename_axis("Person").reset_index(), {
            "Person": "Person", "works": "Works", "avg_score": "Average score", "titles": "Titles"},
            {"works": "{:,.0f}", "avg_score": "{:.1f}"})
