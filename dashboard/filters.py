import math
import streamlit as st
from dashboard import data

# filter widgets keep their value in st.session_state under these keys, every key starts with "f_" so reset can find them
CATEGORY_FILTERS = {
    "type": "Format", "season": "Season", "length": "Length", "status": "Airing status",
    "source": "Source material", "country_of_origin": "Country",
}


def _reset(prefix="f_"):
    for key in [key for key in st.session_state if key.startswith(prefix)]:
        del st.session_state[key]


def _multiselect(df, col, label, prefix="f_"):
    return st.multiselect(label, data.options(df, col), key=f"{prefix}{col}", placeholder="All")


def _range(df, col, spec):
    """slider over the known values of col plus a toggle for works where it is unknown.
    spec: label, unknown_label, step. Returns None when there is nothing to choose"""
    values = df[col].dropna()
    if values.nunique() < 2:
        return None
    low, high = math.floor(values.min()), math.ceil(values.max())
    chosen = st.slider(spec["label"], low, high, (low, high), step=spec.get("step", 1), key=f"f_{col}")

    keep_unknown = True
    if df[col].isna().any():
        keep_unknown = st.toggle(spec["unknown_label"], value=True, key=f"f_{col}_unknown")
    return (*chosen, keep_unknown)


def _english_toggle(show):
    if show:
        st.toggle("Prefer English titles", key="f_english", help="Charts show the English title when there is one.")
    else:
        # pages without charts don't draw it, copying its value keeps Streamlit from dropping it until a chart page
        st.session_state["f_english"] = st.session_state.get("f_english", False)


def render_sidebar(df, english=True):
    """draws the filters and returns them in the shape data.apply_filters expects. english=False hides the
    Prefer English titles toggle, for pages without charts"""
    filters = {"categories": {}, "lists": {}, "ranges": {}}

    with st.sidebar:
        st.markdown("### :material/tune: Filters")
        _english_toggle(english)

        with st.expander(":material/calendar_month: Release", expanded=True):
            filters["ranges"]["year"] = _range(df, "year", {"label": "Year", "unknown_label": "Include unknown year"})
            for col in ["type", "season", "length", "status"]:
                filters["categories"][col] = _multiselect(df, col, CATEGORY_FILTERS[col])

        with st.expander(":material/theater_comedy: Story & content"):
            filters["lists"]["genres"] = (_multiselect(df, "genres", "Genres"),
                                          st.toggle("Must have every genre", key="f_genres_all",
                                                    help="Off: works with any of the chosen genres."))
            filters["lists"]["tags"] = (_multiselect(df, "tags", "Tags"),
                                        st.toggle("Must have every tag", key="f_tags_all"))
            filters["categories"]["source"] = _multiselect(df, "source", CATEGORY_FILTERS["source"])

        with st.expander(":material/movie: Production"):
            filters["lists"]["studio_list"] = (_multiselect(df, "studio_list", "Studios"), False)
            filters["categories"]["country_of_origin"] = _multiselect(df, "country_of_origin", "Country")
            filters["ranges"]["episodes"] = _range(df, "episodes", {"label": "Episodes",
                                                                   "unknown_label": "Include unknown episodes"})

        with st.expander(":material/star: Score"):
            filters["ranges"]["score"] = _range(df, "score", {"label": "Score (0-100)",
                                                             "unknown_label": "Include unscored works"})

        filters["ranges"] = {col: value for col, value in filters["ranges"].items() if value is not None}
        st.button("Reset filters", icon=":material/restart_alt:", on_click=_reset, width="stretch")

    return filters


def render_airing_sidebar(df):
    """the airing page only gets the filters that make sense for works on air, their keys start with "a_" so
    they don't clash with the ones of the list pages"""
    filters = {"categories": {}, "lists": {}, "ranges": {}}

    with st.sidebar:
        st.markdown("### :material/tune: Filters")
        _english_toggle(False)
        filters["categories"]["type"] = _multiselect(df, "type", CATEGORY_FILTERS["type"], "a_")
        filters["lists"]["genres"] = (_multiselect(df, "genres", "Genres", "a_"),
                                      st.toggle("Must have every genre", key="a_genres_all",
                                                help="Off: works with any of the chosen genres."))
        filters["lists"]["tags"] = (_multiselect(df, "tags", "Tags", "a_"),
                                    st.toggle("Must have every tag", key="a_tags_all"))
        filters["lists"]["studio_list"] = (_multiselect(df, "studio_list", "Studios", "a_"), False)
        for col in ["source", "country_of_origin"]:
            filters["categories"][col] = _multiselect(df, col, CATEGORY_FILTERS[col], "a_")
        st.button("Reset filters", icon=":material/restart_alt:", on_click=_reset, args=("a_",), width="stretch")

    return filters


def active_count(filters, df):
    """how many filters differ from their default"""
    count = sum(bool(chosen) for chosen in filters["categories"].values())
    count += sum(bool(chosen) for chosen, _ in filters["lists"].values())
    for col, (low, high, keep_unknown) in filters["ranges"].items():
        values = df[col].dropna()
        count += (low, high) != (math.floor(values.min()), math.ceil(values.max())) or not keep_unknown
    return count
