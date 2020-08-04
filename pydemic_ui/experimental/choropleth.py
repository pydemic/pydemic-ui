import json

import altair as alt
from bokeh.io import show
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar
from bokeh.palettes import brewer
from bokeh.plotting import figure


def choropleth_bokeh(data):
    # See also
    # https://towardsdatascience.com/a-complete-guide-to-an-interactive-geographical
    # Read data to json.

    # Convert to String like object.
    json_data = data.to_json()

    # -map-using-python-f4c5197e23e0
    # Input GeoJSON source that contains features for plotting.
    geosource = GeoJSONDataSource(geojson=json_data)

    # Define a sequential multi-hue color palette.
    palette = brewer["YlGnBu"][8]

    # Reverse color order so that dark blue is highest obesity.
    palette = palette[::-1]

    # Instantiate LinearColorMapper that linearly maps numbers in a range,
    # into a sequence of colors.
    color_mapper = LinearColorMapper(palette=palette, low=0, high=40)
    # Define custom tick labels for color bar.
    tick_labels = {
        "0": "0%",
        "5": "5%",
        "10": "10%",
        "15": "15%",
        "20": "20%",
        "25": "25%",
        "30": "30%",
        "35": "35%",
        "40": ">40%",
    }

    # Create color bar.
    color_bar = ColorBar(
        color_mapper=color_mapper,
        label_standoff=8,
        width=500,
        height=20,
        border_line_color=None,
        location=(0, 0),
        orientation="horizontal",
        major_label_overrides=tick_labels,
    )
    # Create figure object.
    p = figure(
        title="Share of adults who are obese, 2016",
        plot_height=600,
        plot_width=950,
        toolbar_location=None,
    )
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None

    # Add patch renderer to figure.
    p.patches(
        "xs",
        "ys",
        source=geosource,
        fill_color={"field": "per_cent_obesity", "transform": color_mapper},
        line_color="black",
        line_width=0.25,
        fill_alpha=1,
    )

    # Specify figure layout.
    p.add_layout(color_bar, "below")

    # Display figure inline in Jupyter Notebook.
    output_notebook()

    # Display figure.
    show(p)

    # Instantiate LinearColorMapper that maps numbers in a range linearly into a
    # sequence of colors. Input nan_color.
    color_mapper = LinearColorMapper(palette=palette, low=0, high=40, nan_color="#d9d9d9")

    from bokeh.io import curdoc, output_notebook
    from bokeh.models import Slider, HoverTool
    from bokeh.layouts import widgetbox, column

    # Define function that returns json_data for year selected by user.

    def json_data(selectedYear):
        yr = selectedYear
        df_yr = df[df["year"] == yr]
        merged = gdf.merge(df_yr, left_on="country_id", right_on="code", how="left")
        merged.fillna("No data", inplace=True)
        merged_json = json.loads(merged.to_json())
        json_data = json.dumps(merged_json)
        return json_data

    # Input GeoJSON source that contains features for plotting.
    geosource = GeoJSONDataSource(geojson=json_data(2016))
    # Define a sequential multi-hue color palette.
    palette = brewer["YlGnBu"][8]
    # Reverse color order so that dark blue is highest obesity.
    palette = palette[::-1]
    # Instantiate LinearColorMapper that linearly maps numbers in a range,
    # into a sequence of colors. Input nan_color.
    color_mapper = LinearColorMapper(palette=palette, low=0, high=40, nan_color="#d9d9d9")
    # Define custom tick labels for color bar.
    tick_labels = {
        "0": "0%",
        "5": "5%",
        "10": "10%",
        "15": "15%",
        "20": "20%",
        "25": "25%",
        "30": "30%",
        "35": "35%",
        "40": ">40%",
    }
    # Add hover tool
    hover = HoverTool(
        tooltips=[("Country/region", "@country"), ("% obesity", "@per_cent_obesity")]
    )
    # Create color bar.
    color_bar = ColorBar(
        color_mapper=color_mapper,
        label_standoff=8,
        width=500,
        height=20,
        border_line_color=None,
        location=(0, 0),
        orientation="horizontal",
        major_label_overrides=tick_labels,
    )
    # Create figure object.
    p = figure(
        title="Share of adults who are obese, 2016",
        plot_height=600,
        plot_width=950,
        toolbar_location=None,
        tools=[hover],
    )
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    # Add patch renderer to figure.
    p.patches(
        "xs",
        "ys",
        source=geosource,
        fill_color={"field": "per_cent_obesity", "transform": color_mapper},
        line_color="black",
        line_width=0.25,
        fill_alpha=1,
    )
    # Specify layout
    p.add_layout(color_bar, "below")

    # Define the callback function: update_plot
    def update_plot(attr, old, new):
        yr = slider.value
        new_data = json_data(yr)
        geosource.geojson = new_data
        p.title.text = "Share of adults who are obese, %d" % yr

    # Make a slider object: slider
    slider = Slider(title="Year", start=1975, end=2016, step=1, value=2016)
    slider.on_change("value", update_plot)
    # Make a column layout of widgetbox(slider) and plot, and add it to the current
    # document
    layout = column(p, widgetbox(slider))
    curdoc().add_root(layout)
    # Display plot inline in Jupyter notebook
    output_notebook()
    # Display plot
    show(layout)


def choropleth(data, color, tooltip=(), title=_("Map"), color_scheme="bluegreen"):
    """
    Generates Toronto neighbourhoods map with building count choropleth
    """
    # This method doesn't work with streamlit.
    # See more: https://medium.com/dataexplorations/creating-choropleth-maps-in-altair
    # -eeb7085779a1

    # scale = alt.Scale(scheme=color_scheme)
    # color = alt.Color(color, type='quantitative', scale=scale, title="Title")
    data = alt.InlineData
    alt.DataFormat
    base = (
        alt.Chart(data, title=title)
        .mark_geoshape(stroke="black", strokeWidth=1)
        .encode()
        # .properties(width=800, height=800)
    )

    # choro = (
    #     alt.Chart(data)
    #         .mark_geoshape(fill='lightgray', stroke='black')
    #         .encode(color, tooltip=tooltip)
    # )

    return base
