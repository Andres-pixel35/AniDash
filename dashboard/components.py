import html
import pandas as pd
import streamlit as st
from dashboard import data
from dashboard.data import UNKNOWN

CSS = """
<style>
.block-container {max-width: 1380px; padding-top: 3.2rem;}
/* neutral tones are mixed from the text color, so the same rules fit the Mocha and Latte themes */
.hero {padding: .4rem 0 1.2rem; margin-bottom: 1.2rem; border-bottom: 1px solid color-mix(in srgb, currentColor 14%, transparent);}
.hero-eyebrow {font-size: .82rem; opacity: .75;}
.hero-title {font-size: 2rem; font-weight: 600; line-height: 1.2; margin-top: .2rem; letter-spacing: -.01em;}
.hero-sub {opacity: .78; margin-top: .45rem; font-size: 1rem; max-width: 720px;}
.hero-chip {
    display: inline-block; border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
    border-radius: 999px; padding: .15rem .75rem; font-size: .8rem; opacity: .8; margin: .8rem .45rem 0 0;
}
.kpi {
    border: 1px solid color-mix(in srgb, currentColor 12%, transparent); border-radius: 12px;
    padding: 1rem 1.15rem .95rem; background: color-mix(in srgb, currentColor 3%, transparent);
    min-height: 118px; margin-bottom: .9rem;
}
.kpi-label {font-size: .82rem; opacity: .75;}
.kpi-value {font-size: 1.65rem; font-weight: 600; line-height: 1.2; margin-top: .25rem; overflow-wrap: anywhere;}
.kpi-value.long {font-size: 1.1rem; line-height: 1.3;}
.kpi-sub {font-size: .8rem; opacity: .72; margin-top: .35rem;}
.work-synopsis {white-space: pre-wrap; line-height: 1.55; opacity: .92;}
</style>
"""
# on the Latte background faded text (opacity, Streamlit's caption gray) is too light: use Latte subtext1 instead
LIGHT_CSS = """
<style>
.hero-eyebrow, .hero-sub, .hero-chip, .kpi-label, .kpi-sub {opacity: 1; color: #5C5F77;}
[data-testid="stCaptionContainer"] {color: #5C5F77;}
</style>
"""


def inject_css():
    st.markdown(CSS if st.context.theme.type == "dark" else CSS + LIGHT_CSS, unsafe_allow_html=True)


def esc(value):
    return html.escape(str(value))


def page_data():
    """the filtered works set by streamlit_app.py; stops the page when the filters leave nothing"""
    df = st.session_state["filtered"]
    if df.empty:
        st.warning("No works match the current filters. Loosen them or press **Reset filters** in the sidebar.",
                   icon=":material/filter_alt_off:")
        st.stop()
    return df


def hero(eyebrow, title, subtitle, chips=()):
    chips_html = "".join(f'<span class="hero-chip">{esc(chip)}</span>' for chip in chips)
    st.markdown(
        f'<div class="hero"><div class="hero-eyebrow">{esc(eyebrow)}</div><div class="hero-title">{esc(title)}</div>'
        f'<div class="hero-sub">{esc(subtitle)}</div>{chips_html}</div>',
        unsafe_allow_html=True,
    )


def kpis(cards, per_row=4, titles=False):
    """cards: [(label, value, sub)]. Words longer than a short number (titles, names) get a smaller font,
    titles=True gives it to every card"""
    for start in range(0, len(cards), per_row):
        for col, (label, value, sub) in zip(st.columns(per_row), cards[start:start + per_row]):
            value = str(value)
            size = " long" if titles or (len(value) > 8 and not value[0].isdigit()) or len(value) > 13 else ""
            col.markdown(
                f'<div class="kpi"><div class="kpi-label">{esc(label)}</div>'
                f'<div class="kpi-value{size}">{esc(value)}</div><div class="kpi-sub">{esc(sub)}</div></div>',
                unsafe_allow_html=True,
            )


def selection_key(name, df):
    """key for a selectable table that changes with the works it shows: a selection is a row position, so when
    filters or views change the rows, the old selection is dropped instead of pointing to another work or past
    the end of the table"""
    return f"{name}_{hash(tuple(df['anime_id']))}"


def section(title, caption=None):
    st.subheader(title, divider="gray")
    if caption:
        st.caption(caption)


def _is_missing(value):
    if isinstance(value, list):
        return not value
    return pd.isna(value) or value == UNKNOWN


def missing_note(df, col, what):
    """caption telling how many works were left out of a chart because col is unknown or empty"""
    missing = int(df[col].map(_is_missing).sum())
    if missing:
        works = "work" if missing == 1 else "works"
        st.caption(f":material/info: {missing} {works} with unknown {what} not shown.")


def top_n(label, available, default, key):
    """slider for how many items to show; with 5 or fewer items there is nothing to choose"""
    if available <= 5:
        return available
    return st.slider(label, 5, min(60, available), min(default, available), key=key)


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def table(df, columns, formats=None):
    """small read-only table: columns {field: label}, Unknown for missing values"""
    view = df[list(columns)].rename(columns=columns)
    styler = view.style.format(na_rep=UNKNOWN)
    if formats:
        styler = styler.format({columns[k]: v for k, v in formats.items()}, na_rep=UNKNOWN)
    # a capped first column (the title) keeps long names from pushing the other columns out of view
    first = st.column_config.Column(width="medium") if len(columns) > 3 else None
    st.dataframe(styler, hide_index=True, width="stretch", column_config={view.columns[0]: first} if first else None)



PICKABLE = [col for col in data.LABELS if col not in ("name", "synopsis")]
FORMATS = {
    "episodes": "{:,.0f}", "duration": "{:,.0f}", "watch_hours": "{:,.1f}", "score": "{:.0f}", "mean_score": "{:.0f}",
    "popularity": "{:,.0f}", "favorites": "{:,.0f}", "favorite_rate": "{:.1f}", "watching": "{:,.0f}",
    "completed": "{:,.0f}", "on_hold": "{:,.0f}", "dropped": "{:,.0f}", "plan_to_watch": "{:,.0f}",
    "completion_rate": "{:.0%}", "drop_rate": "{:.0%}",
}


def column_table(df, default, key, height=480):
    """multiselect of columns above a selectable table of df; returns the table event and the shown (labelled) view.
    Widget keys are f"{key}_columns" and f"{key}_table" """
    columns = st.multiselect("Columns", PICKABLE, default=default, format_func=data.LABELS.get, key=f"{key}_columns")
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
    styler = view.style.format(na_rep=UNKNOWN).format(
        {data.LABELS[col]: fmt for col, fmt in FORMATS.items() if col in columns}, na_rep=UNKNOWN)
    link = {data.LABELS["site_url"]: st.column_config.LinkColumn(data.LABELS["site_url"], display_text="Open")}
    event = st.dataframe(styler, hide_index=True, width="stretch", height=height, on_select="rerun",
                         selection_mode="single-row", key=selection_key(f"{key}_table", df), column_config=link)
    return event, view


def text(value, fmt=None):
    """value formatted with fmt (as is without it), lists joined with commas, Unknown when missing"""
    if isinstance(value, list):
        return ", ".join(value) if value else UNKNOWN
    if value is None or pd.isna(value):
        return UNKNOWN
    return format(value, fmt) if fmt else str(value)


def work_card(work):
    """every detail of one work: names, badges, kpis, dates, credits and synopsis"""
    with st.container(border=True):
        st.markdown(f"### {esc(work['title'])}")
        other_names = " · ".join(text(work[col]) for col in ["english_title", "japanese_title"] if pd.notna(work[col]))
        if other_names:
            st.caption(other_names)
        badges = [work["type"], text(work["year"]), work["season"], work["status"], work["source"], work["length"]]
        st.markdown(" ".join(f":blue-badge[{esc(b)}]" for b in badges if b != data.UNKNOWN))

        kpis([
            ("Score", text(work["score"], ".0f"), f"Mean user score {text(work['mean_score'], '.0f')}"),
            ("Episodes", text(work["episodes"], ",.0f"), f"{text(work['duration'], '.0f')} min each"),
            ("Watch time", f"{text(work['watch_hours'], ',.1f')} h", "Episodes × duration"),
            ("Popularity", text(work["popularity"], ",.0f"), f"{text(work['favorites'], ',.0f')} favorites"),
        ])

        info, story = st.columns([2, 3], gap="large")
        with info:
            for col in ["start_date", "end_date"]:
                value = work[col]
                st.markdown(f"**{data.LABELS[col]}:** {value:%d %B %Y}" if pd.notna(value) else f"**{data.LABELS[col]}:** {data.UNKNOWN}")
            for col in ["studio_list", "genres", "country_of_origin", "streaming_sites"]:
                st.markdown(f"**{data.LABELS[col]}:** {esc(text(work[col]))}")
            st.markdown(f"**{data.LABELS['tags']}:** " + (" ".join(f":gray-badge[{esc(t)}]" for t in work["tags"])
                                                     or data.UNKNOWN))
        with story:
            synopsis = work["synopsis"] if pd.notna(work["synopsis"]) else "No synopsis available."
            st.markdown(f'<div class="work-synopsis">{esc(synopsis)}</div>', unsafe_allow_html=True)
            with st.expander("Staff and characters"):
                st.markdown(f"**{data.LABELS['main_staff']}:** {esc(text(work['main_staff']))}")
                st.markdown(f"**{data.LABELS['main_characters']}:** {esc(text(work['main_characters']))}")
            if pd.notna(work["site_url"]):
                st.link_button("Open on AniList", work["site_url"], icon=":material/open_in_new:")
