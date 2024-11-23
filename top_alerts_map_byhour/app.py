from shiny import App, reactive, ui
import pandas as pd
import altair as alt
import geopandas as gpd
from shinywidgets import render_altair, output_widget
import json
from datetime import datetime

#load data
time_waze_df = pd.read_csv(
    r"C:\\Users\\Mitch\\Documents\\GitHub\\problem-set-6\\top_alerts_map_byhour\\top_alerts_map_byhour.csv"
)
#convert hour to string, will need it in this format later
time_waze_df["hour"]=pd.to_datetime(time_waze_df["hour"],format="%H:%M")

#dropdown menu choices
menu_choices = (
    time_waze_df[["type", "updated_subtype"]]
    .drop_duplicates()
    .apply(lambda row: f"{row['type']} - {row['updated_subtype']}", axis=1)
    .tolist()
)

# Load GeoJSON data and transform to WGS84
file_path = r"C:\\Users\\Mitch\\Documents\\GitHub\\problem-set-6\\top_alerts_map\\Boundaries - Neighborhoods.geojson"
neighborhoods = gpd.read_file(file_path)

# Ensure GeoJSON data is in WGS84
neighborhoods = neighborhoods.to_crs(epsg=4326)

# Convert GeoJSON to Altair-friendly format
neighborhoods_json = json.loads(neighborhoods.to_json())
geo_data = alt.Data(values=neighborhoods_json["features"])



app_ui = ui.page_fluid(
    ui.panel_title("Traffic Incidents in Chicago"),
    ui.input_select(
        id="incident",
        label="Choose a type",
        choices=menu_choices,
    ),
    ui.input_slider(label="Hour of Day (military time)",
                    id="hour",
                    min=1,
                    max=24,
                    step=1,
                    value=1),
    output_widget("chart"))

def server(input, output, session):
    @reactive.Calc
    def full_data():
        return time_waze_df

    @reactive.Calc
    def subsetted_data():
        df = full_data()
        selected_type, selected_subtype = input.incident().split(" - ")
        selected_hour = datetime.strptime(f"{input.hour()}:00", "%H:%M")
        return df[(df["type"] == selected_type) & (df["updated_subtype"] == selected_subtype)
                  & (df["hour"]==selected_hour)]

    @render_altair
    def chart():
        filtered_data = subsetted_data()

        # Define min and max latitude/longitude
        min_latitude = time_waze_df["latitude"].min()
        max_latitude = time_waze_df["latitude"].max()
        min_longitude = time_waze_df["longitude"].min()
        max_longitude = time_waze_df["longitude"].max()

        # Create the jams chart
        jams_chart = (
            alt.Chart(filtered_data)
            .mark_circle()
            .encode(
                alt.X(
                    "longitude",
                    scale=alt.Scale(domain=[min_longitude, max_longitude]),
                ),
                alt.Y(
                    "latitude",
                    scale=alt.Scale(domain=[min_latitude, max_latitude]),
                ),
                size="count",
            )
            .transform_window(
                rank="rank(count)",
                sort=[alt.SortField("count", order="descending")],
            )
            .transform_filter(
                alt.datum.rank <= 10
            )
            .properties(title="Top 10 Locations for Selected Incident at Selected Time in Chicago")
        )

        # Define the base map
        base_map = (
            alt.Chart(geo_data)
            .mark_geoshape()
            .encode(fill=alt.value("grey"))
            .project(type="identity", reflectY=True)  # Identity projection for WGS84
        )

        # Combine the base map and jams chart
        combined_chart = (base_map + jams_chart).project(type="identity", reflectY=True)

        # Return the Altair chart for rendering
        return combined_chart

    # Bind the chart output
    output.chart = chart



app=App(app_ui,server)
