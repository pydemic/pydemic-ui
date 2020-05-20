__package__ = "pydemic_ui.components"

import altair as alt

from pydemic.utils import fmt
from .base import main_component


@main_component()
def pyramid_chart(data, left="left", right="right", hleft=fmt, hright=fmt, where=None):
    """
    A Population pyramid chart.

    Args:
        data:
            Input dataframe with ["left", "right"] columns.
        left:
            Name of the column that will be displayed to the left.
        right:
            Name of the column that will be displayed to the right.
        hleft:
            Humanized left column or function.
        hright:
            Humanized right column or function.
    """
    cols = ["left", "right"]
    titles = [left, right]
    directions = ["descending", "ascending"]
    h_cols = [left, right]

    # Transform datasets
    data = data.copy()
    data["index"] = [str(x) for x in data.index]
    data["color_left"] = "A"
    data["color_right"] = "B"

    if callable(hleft):
        data[h_cols[0]] = data["left"].apply(hleft)
    else:
        data[h_cols[0]] = hleft

    if callable(hright):
        data[h_cols[1]] = data["right"].apply(hright)
    else:
        data[h_cols[1]] = hright
    data = data.loc[::-1]

    # Chart
    base = alt.Chart(data)
    height = 250
    width = 300

    def piece(i):
        return (
            base.mark_bar()
            .encode(
                x=alt.X(cols[i], title=None, sort=alt.SortOrder(directions[i])),
                y=alt.Y("index", axis=None, title=None, sort=alt.SortOrder("descending")),
                tooltip=alt.Tooltip([h_cols[i]]),
                color=alt.Color(f"color_{cols[i]}:N", legend=None),
            )
            .properties(title=titles[i], width=width, height=height)
            .interactive()
        )

    where.altair_chart(
        alt.concat(
            piece(0),
            base.encode(
                y=alt.Y("index", axis=None, sort=alt.SortOrder("descending")),
                text=alt.Text("index"),
            )
            .mark_text()
            .properties(width=50, height=height),
            piece(1),
            spacing=5,
        ),
        use_container_width=False,
    )


if __name__ == "__main__":
    import streamlit as st
    import pandas as pd

    df = pd.DataFrame({"left": [1, 2, 3, 4], "right": [4, 3, 2, 1]})
    st.header("Charts")

    st.subheader("pyramid_chart()")
    pyramid_chart(df, "first", "second")
