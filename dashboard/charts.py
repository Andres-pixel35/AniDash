"""Altair charts. Colors come from the theme in .streamlit/config.toml unless a mark needs a fixed one.
Every function takes already prepared data (no NaN in the plotted fields) and a spec dict with the titles/options.
Streamlit fits the whole chart, axes and legend included, into its height, so default heights add room for them."""

import altair as alt
import pandas as pd
import streamlit as st

# lists of thousands of works explode into more rows than Altair's default limit
alt.data_transformers.disable_max_rows()

# Catppuccin Latte accent -> the same accent in Mocha. Colors are given in Latte and swapped in dark mode
MOCHA = {
    "#DC8A78": "#F5E0DC", "#DD7878": "#F2CDCD", "#EA76CB": "#F5C2E7", "#8839EF": "#CBA6F7", "#D20F39": "#F38BA8",
    "#E64553": "#EBA0AC", "#FE640B": "#FAB387", "#DF8E1D": "#F9E2AF", "#40A02B": "#A6E3A1", "#179299": "#94E2D5",
    "#04A5E5": "#89DCEB", "#209FB5": "#74C7EC", "#1E66F5": "#89B4FA", "#7287FD": "#B4BEFE", "#8C8FA1": "#7F849C",
}
# sequential colors in dark mode: low values Mocha surface1, high values pink
DARK_RAMP = ["#45475A", "#CBA6F7", "#F5C2E7"]
ACCENT = "#FE640B"  # peach, apart from the mauve of the first series


def _dark():
    return st.context.theme.type == "dark"


def tone(color):
    """a Latte color, or its Mocha twin in dark mode"""
    return MOCHA.get(color.upper(), color) if _dark() else color


def ink():
    """text/line color that reads on the current theme background"""
    return "#CDD6F4" if _dark() else "#4C4F69"


def _rows(chart):
    """rows of data behind a chart or the biggest of its layers"""
    if isinstance(getattr(chart, "data", None), pd.DataFrame):
        return len(chart.data)
    return max((_rows(layer) for layer in getattr(chart, "layer", [])), default=0)


def show(chart):
    if _rows(chart) == 0:
        st.info("Nothing to show here with the current data.", icon=":material/bar_chart_off:")
        return
    # no grid inside the plot, only the x and y axis lines
    axis = {"grid": False, "domain": True}
    if _dark():
        # config.toml holds the Latte chart colors for both modes, the chart's own config wins over it
        categorical = [tone(color) for color in st.get_option("theme.chartCategoricalColors")]
        chart = chart.configure_range(category=categorical, ramp=DARK_RAMP)
    else:
        # Streamlit's faded label gray is too light on the Latte background
        axis.update(labelColor=ink(), titleColor=ink())
        chart = chart.configure_legend(labelColor=ink(), titleColor=ink())
    chart = chart.configure_axis(**axis)
    st.altair_chart(chart, width="stretch")


def _color(data, field, spec, **kwargs):
    """nominal colour for field. With spec["palette"] ({value: colour}) every value keeps its own colour,
    whatever other values the filters leave in the data"""
    palette = spec.get("palette")
    if palette:
        present = [value for value in palette if value in set(data[field])]
        kwargs.update(scale=alt.Scale(domain=present, range=[tone(palette[value]) for value in present]), sort=present)
    else:
        kwargs.setdefault("sort", spec.get("color_sort"))
    return alt.Color(f"{field}:N", **kwargs)


def _tooltip(fields):
    """fields: [(field, title, format or None)]"""
    return [alt.Tooltip(field, title=title, format=fmt) if fmt else alt.Tooltip(field, title=title)
            for field, title, fmt in fields]


def ranked_bar(data, cat, val, spec):
    """horizontal bars sorted by val. spec: val_title, format, tooltip (extra [(field, title, fmt)]), height,
    label ((field, fmt) shown at the bar end instead of val)"""
    fmt = spec.get("format", ",.0f")
    base = alt.Chart(data).encode(
        y=alt.Y(f"{cat}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260, labelOverlap=False)),
        # extra room on the right so the value labels past the longest bar aren't cut
        x=alt.X(f"{val}:Q", title=spec["val_title"], axis=alt.Axis(format=fmt, grid=False),
                scale=alt.Scale(domain=[0, max(data[val].max(), 0) * 1.2 or 1])),
        tooltip=_tooltip([(f"{cat}:N", spec.get("cat_title", "Name"), None), (f"{val}:Q", spec["val_title"], fmt),
                          *spec.get("tooltip", [])]),
    )
    bars = base.mark_bar(cornerRadiusEnd=5, height={"band": 0.75})
    label_field, label_fmt = spec.get("label", (val, fmt))
    labels = base.mark_text(align="left", dx=5, color=ink(), fontSize=12).encode(
        text=alt.Text(f"{label_field}:Q", format=label_fmt))
    return (bars + labels).properties(height=spec.get("height", max(140, 28 * len(data) + 50)))


def histogram(values, spec):
    """values: Series without NaN. spec: title, bins"""
    data = pd.DataFrame({"value": values})
    bin_ = alt.Bin(maxbins=spec.get("bins", 20))
    bars = alt.Chart(data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.55).encode(
        x=alt.X("value:Q", bin=bin_, title=spec["title"]),
        y=alt.Y("count():Q", title="Works"),
        tooltip=[alt.Tooltip("value:Q", bin=bin_, title=spec["title"]), alt.Tooltip("count():Q", title="Works")],
    )
    return bars.properties(height=300)


def boxplot(data, cat, val, spec):
    """one horizontal box per cat, sorted by median, with the number of works in the label.
    spec: val_title, height, scale ("log" for long tailed values)"""
    sizes = data.groupby(cat)[val].size()
    data = data.assign(**{cat: data[cat].map(lambda c: f"{c} ({sizes[c]})")})
    order = data.groupby(cat)[val].median().sort_values(ascending=False).index.tolist()

    return alt.Chart(data).mark_boxplot(
        extent=1.5, size=16, median={"color": ink(), "strokeWidth": 2}, rule={"color": ink(), "opacity": 0.6},
        ticks={"color": ink(), "opacity": 0.6}, outliers={"size": 22, "opacity": 0.65},
    ).encode(
        y=alt.Y(f"{cat}:N", sort=order, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X(f"{val}:Q", title=spec["val_title"], scale=alt.Scale(type=spec.get("scale", "linear"), zero=False)),
    ).properties(height=spec.get("height", max(180, 44 * len(order) + 60)))


def stacked_columns(data, x, color, spec):
    """data: x, color, value already counted. spec: y_title, format, color_title, color_sort or palette"""
    fmt = spec.get("format", ",.0f")
    return alt.Chart(data).mark_bar(opacity=0.95).encode(
        x=alt.X(f"{x}:O", title=None, sort="ascending", axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
        y=alt.Y("value:Q", title=spec["y_title"], stack="zero", axis=alt.Axis(format=fmt)),
        color=_color(data, color, spec, title=spec.get("color_title"), legend=alt.Legend(orient="bottom", columns=6)),
        order=alt.Order("value:Q", sort="descending"),
        tooltip=_tooltip([(f"{x}:O", spec.get("x_title", x), None), (f"{color}:N", spec.get("color_title", color), None),
                          ("value:Q", spec["y_title"], fmt)]),
    ).properties(height=spec.get("height", 340))


def columns(data, x, val, spec):
    """single series of vertical bars. spec: y_title, x_title, format"""
    fmt = spec.get("format", ",.0f")
    return alt.Chart(data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X(f"{x}:O", title=None, sort="ascending", axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
        y=alt.Y(f"{val}:Q", title=spec["y_title"], axis=alt.Axis(format=fmt)),
        tooltip=_tooltip([(f"{x}:O", spec.get("x_title", x), None), (f"{val}:Q", spec["y_title"], fmt)]),
    ).properties(height=spec.get("height", 320))


def trend_band(data, x, spec):
    """data: x, mean, q1, q3, n. Line of the mean with a band from the 25th to the 75th percentile"""
    base = alt.Chart(data).encode(x=alt.X(f"{x}:O", title=None, axis=alt.Axis(labelAngle=-45, labelOverlap=True)))
    band = base.mark_area(opacity=0.22).encode(
        y=alt.Y("q1:Q", title=spec["y_title"], scale=alt.Scale(zero=False)), y2="q3:Q",
    )
    line = base.mark_line(point=alt.OverlayMarkDef(size=45, filled=True), strokeWidth=2.5).encode(
        y="mean:Q",
        tooltip=_tooltip([(f"{x}:O", spec.get("x_title", x), None), ("mean:Q", "Average", ".1f"),
                          ("q1:Q", "25th percentile", ".1f"), ("q3:Q", "75th percentile", ".1f"),
                          ("n:Q", "Works", ",.0f")]),
    )
    return (band + line).properties(height=spec.get("height", 320))


def heatmap(data, x, y, spec):
    """data: x, y, value. spec: value_title, x_sort, y_sort, format, x_title, y_title, x_label_angle"""
    fmt = spec.get("format", ",.0f")
    return alt.Chart(data).mark_rect(cornerRadius=3, stroke=None).encode(
        x=alt.X(f"{x}:O", title=None, sort=spec.get("x_sort"),
                axis=alt.Axis(labelAngle=spec.get("x_label_angle", -45), labelOverlap=True)),
        y=alt.Y(f"{y}:O", title=None, sort=spec.get("y_sort"), axis=alt.Axis(labelLimit=200, labelOverlap=False)),
        # legend on the side: the chart height includes the legend, a bottom one would squash the rows
        color=alt.Color("value:Q", title=spec["value_title"], legend=alt.Legend(orient="right", gradientLength=120)),
        tooltip=_tooltip([(f"{y}:O", spec.get("y_title", y), None), (f"{x}:O", spec.get("x_title", x), None),
                          ("value:Q", spec["value_title"], fmt)]),
    ).properties(height=spec.get("height", max(220, 30 * data[y].nunique() + 90)))


def scatter(data, x, y, spec):
    """spec: x_title, y_title, tooltip [(field, title, fmt)], color (nominal field), color_sort or palette,
    size (quantitative field), x_scale / y_scale ("linear" or "log"), trend (adds a dashed trend that is straight
    on the chosen scales)"""
    x_enc = alt.X(f"{x}:Q", title=spec["x_title"], scale=alt.Scale(type=spec.get("x_scale", "linear"), zero=False))
    y_enc = alt.Y(f"{y}:Q", title=spec["y_title"], scale=alt.Scale(type=spec.get("y_scale", "linear"), zero=False))
    encoding = {"x": x_enc, "y": y_enc, "tooltip": _tooltip(spec["tooltip"])}
    if spec.get("color"):
        encoding["color"] = _color(data, spec["color"], spec, title=None, legend=alt.Legend(orient="bottom", columns=6))
    if spec.get("size"):
        encoding["size"] = alt.Size(f"{spec['size']}:Q", scale=alt.Scale(range=[25, 420]), legend=None)

    points = alt.Chart(data).mark_circle(opacity=0.72, stroke=ink(), strokeWidth=0.3).encode(**encoding)
    chart = points
    if spec.get("trend") and len(data) > 2:
        trend = alt.Chart(data).mark_line(color=tone(ACCENT), strokeDash=[6, 4], strokeWidth=2).encode(x=x_enc, y=y_enc)
        method = {("log", "log"): "pow", ("log", "linear"): "log", ("linear", "log"): "exp"}.get(
            (spec.get("x_scale", "linear"), spec.get("y_scale", "linear")), "linear")
        chart = points + trend.transform_regression(x, y, method=method)
    return chart.properties(height=spec.get("height", 420)).interactive()
