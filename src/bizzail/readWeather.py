from bs4 import BeautifulSoup as bs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime as dt
from collections import defaultdict
import pathlib
import re
import requests
import json
from .utils import speedUnits, angleUnits
from .constants import *

from typing import Union, Literal, Optional

Locations = Literal["zurich", "costa nova"]

# TODO:
# check that model is in GURU models; error handling if page not fully loaded yet
# plot comparison of different models
# query actual values from meteoswiss -> download csv table
# Swiss Meteo stations in Fluntern, Waedenswil, and Zueri Affoltern
# -> can historic data be extracted?
# Extract historic wind predictions from different models in Guru? possible?


class WindInfo:
    def __init__(self, headless: bool = True):

        self._driver = None
        self._forecast = defaultdict(lambda: pd.DataFrame)
        self._actuals = defaultdict(lambda: pd.DataFrame)
        self._soups = dict()

        self._headless = headless

    @property
    def driver(self):

        if self._driver is None:

            from msedge.selenium_tools import EdgeOptions
            from msedge.selenium_tools import Edge

            edge_options = EdgeOptions()
            edge_options.use_chromium = True

            if self._headless:
                edge_options.add_argument("headless")
                edge_options.add_argument("disable-gpu")
            else:
                edge_options = None

            self._driver = Edge(
                executable_path=pathlib.Path.cwd().joinpath(
                    "driver/MicrosoftWebDriver.exe"
                ),
                options=edge_options,
            )

            self._driver.implicitly_wait(10)

        return self._driver

    @property
    def actuals(
        self, location: Optional[Locations] = None, source: Optional[str] = None
    ):

        if location is None:
            # get the first location
            location = list(self._actuals.keys())[0]
        df = self._actuals[location]

        if source is None:
            # get the first source
            source = df["Source"].unique()[0]
        df = df.loc[df["Source"] == source, df.columns != "Source"]

        return df

    @property
    def forecast(
        self, location: Optional[Locations] = None, model: Optional[str] = None
    ):

        if location is None:
            # get the first location
            location = list(self._forecast.keys())[0]
        df = self._forecast[location]

        if model is None:
            # get the first model
            model = df["Model"].unique()[0]
        df = df.loc[
            df["Model"] == model,
            [col for col in df.columns if col not in ("Wind direction")],
        ]

        return df

    # TODO: have dictionary of favorite locations so can use name only
    def _getGuruSoup(self, location: Locations):

        id = GURU_LOCATIONS[location]

        url = GURU_URI + str(id)
        self.driver.get(url)

        element_present = EC.presence_of_element_located((By.ID, "tabid_0_0_dates"))
        WebDriverWait(self.driver, 20).until(element_present)

        self._soups.update(
            {location: {"guru": bs(self.driver.page_source, features="lxml")}}
        )

    def _getGuruTabId(self, soup, model):

        legends = soup.find_all("div", {"class": "nadlegend"})

        legendIndex = [
            i for i, leg in enumerate(legends) if bool(re.search(model, leg.text))
        ][0]

        return legends[legendIndex].parent.parent.attrs["data-id"]

    def _parseGuruSoup(self, location, model):

        if (location not in self._soups.keys()) or (
            "guru" not in self._soups[location].keys()
        ):
            self._getGuruSoup(location)

        soup = self._soups[location]["guru"]
        tabid = self._getGuruTabId(soup, model)

        dates = soup.find_all("tr", id=f"{tabid}_0_dates")[0]
        today = dt.today()

        forecastDates = []
        for dayHour in dates.find_all("td"):
            vals = re.sub(
                r"(\w{2})(\d{1,2})[.](\d{2})h", r"\1 \2 \3", dayHour.text
            ).split()
            forecastDates.append((vals[0], int(vals[1]), int(vals[2])))

        firstDate = dt(today.year, today.month, int(forecastDates[0][1]))
        lastDate = firstDate.day
        timestamps = []
        # TODO this doesn't look right
        for day in forecastDates:
            if day[1] >= lastDate:
                month = today.month
            else:
                month = today.month + 1
            timestamps.append(dt(today.year, today.month, day[1], day[2]))

        myData = dict(Timestamp=timestamps)
        for info in GURU_INFO.values():
            if info != "SMER":
                myData[info] = [
                    prop.text for prop in soup.find("tr", id=f"{tabid}_0_{info}")
                ]
            else:
                # wind direction needs to be treated differently
                directions = [
                    prop.find("span").attrs["title"]
                    for prop in soup.find("tr", id=f"{tabid}_0_{info}")
                ]

                myData["SMER"] = directions

                # parse the string, get the directions and angles
                descriptions_angles = [
                    re.sub(r"(\w{1,3}) \((\d{1,3}[.]?\d{0,2}).*", r"\1 \2", d).split()
                    for d in directions
                ]

                # round the angles correctly to the next integer
                descriptions, angles = zip(
                    *map(
                        lambda x: (x[0], round(float(x[1]))),
                        descriptions_angles,
                    )
                )

                myData["Wind direction (description)"] = descriptions
                myData["Wind direction (angle)"] = angles

        # TODO: formatting of timestamp col and col descriptions?
        df = pd.DataFrame(myData)

        df[NUMERIC_INFO] = (
            df[NUMERIC_INFO].apply(pd.to_numeric, errors="coerce").fillna(0)
        )
        df = df.rename(columns=dict(zip(GURU_INFO.values(), GURU_INFO.keys())))

        df["Model"] = model
        df["Source"] = "Windguru"

        self._forecast[location] = df

    def _getMeteoCsvs(self, station="fluntern"):

        df = pd.DataFrame(
            columns=[
                "Timestamp",
                "Wind speed [kn]",
                "Wind gusts [kn]",
                "Wind direction (description)",
                "Wind direction (angle)",
                "Temperature [C]",
                "Precipitation [mm/h]",
                "Model",
                "Source",
            ]
        )

        interestingCols = (
            "Messdatum",
            "Böen km/h",
            "Windrichtung °",
            "Wind km/h",
            "Niederschlag mm",
            "Temperature °C",
        )

        df_tot = pd.DataFrame()
        for info in (METEO_TEMP, METEO_RAIN, METEO_SPEED, METEO_GUSTS):
            dfloc = pd.read_csv(info, sep=";", encoding="latin")

            dfloc = dfloc.loc[dfloc["Abk."] == METEO_LOCATIONS[station]]
            df_tot = pd.concat(
                (
                    df_tot,
                    dfloc.melt(
                        value_vars=[
                            col for col in dfloc.columns if col in interestingCols
                        ]
                    ),
                ),
            )

        # checks
        # there should only be one timestamp
        if len(df_tot.groupby("variable")["value"].unique().loc["Messdatum"]) > 1:
            raise ValueError(
                "The station had multiple Timestamps for different properties."
            )

        # wind angle shouldn't differ too much between gust and wind speed
        if df_tot.loc[df_tot.variable == "Windrichtung °", "value"].diff().max() > 10:
            raise ValueError("Wind angles for gust and speed are very different.")

        df_tot = df_tot.drop_duplicates(ignore_index=True)
        df_tot["obs"] = 0
        df_tot = df_tot.pivot(
            index="obs", values="value", columns="variable"
        ).reset_index(drop=True)

        df["Source"] = "swissmeteo"

        # TODO: convert units, rearrange into right order

        return df_tot

    def _getZurichApi(
        self,
        station="mythenquai",
        startDate=None,
        endDate=None,
        limit=500,
        offset=0,
    ):

        # interestingly, the below fails in a list comprehension
        params = []
        for x in ["startDate", "endDate", "limit", "offset"]:
            if eval(x) is not None:
                params.append(f"{x}={eval(x)}")

        params = ["sort=timestamp_cet%20desc"] + params

        queryStr = f"{ZURICH_API}{station}?{'&'.join(params)}"

        return json.loads(requests.get(queryStr).content)["result"]

    def _parseZurichApi(self, response):
        df = pd.DataFrame([el["values"] for el in response])
        df = df.applymap(lambda x: x["value"])

        df["timestamp_cet"] = pd.to_datetime(df["timestamp_cet"]).dt.tz_localize(None)

        df_kn = df.loc[:, ["wind_speed_avg_10min", "wind_gust_max_10min"]].apply(
            lambda x: self.unitConverter(x, "ms", "kn")
        )
        df_kn.columns = ["wind_speed_avg_10min_kn", "wind_gust_max_10min_kn"]
        # convert wind speeds to knots
        df = pd.merge(
            df,
            df_kn,
            left_index=True,
            right_index=True,
        )

        df["Source"] = "zurich"

        df["Wind direction (description)"] = df["wind_direction"].apply(
            lambda x: self.unitConverter(x, "degrees", "direction")
        )

        df = df.rename(
            columns={
                "timestamp_cet": "Timestamp",
                "air_temperature": "Temperature [C]",
                "wind_gust_max_10min_kn": "Wind gusts [kn]",
                "wind_speed_avg_10min": "Wind speed [kn]",
                "wind_direction": "Wind direction (angle)",
                "precipitation": "Precipitation [mm/h]",
            }
        )

        df = df[
            [
                "Timestamp",
                "Wind speed [kn]",
                "Wind gusts [kn]",
                "Wind direction (description)",
                "Wind direction (angle)",
                "Temperature [C]",
                "Precipitation [mm/h]",
                "Source",
            ]
        ]

        self._actuals["zurich"] = df

        # TODO, store the same info as we do for forecasts

    def _getZurich(self, station="mythenquai", startDate=None, endDate=None, api=True):
        if api:
            apiResponse = self._getZurichApi(
                station=station, startDate=startDate, endDate=endDate
            )
            self._parseZurichApi(apiResponse)
        else:
            raise NotImplementedError("Can only query ZH weather actuals via API.")

    def getActuals(
        self, location="zurich", source: Literal["zurich", "swissmeteo"] = "zurich"
    ):
        if location == "zurich" and source == "zurich":
            self._getZurich()
        else:
            raise NotImplementedError(
                "Only know how to query Zurich actuals from Zurich weather station API."
            )

    def getForecast(self, location="zurich", model="WG"):

        location = location.lower()

        if location not in [loc.lower() for loc in GURU_LOCATIONS.keys()]:
            raise ValueError(f"Location {location} is unknown.")

        if model in GURU_MODELS:
            self._parseGuruSoup(location, model)

    @classmethod
    def unitConverter(cls, value, inputUnit, outputUnit):

        if inputUnit in speedUnits["to"].keys():
            value_kn = speedUnits["to"][inputUnit](value)
            value_output = speedUnits["from"][outputUnit](value_kn)
        elif inputUnit in angleUnits["to"].keys():
            value_angle = angleUnits["to"][inputUnit](value)
            value_output = angleUnits["from"][outputUnit](value_angle)

        return value_output
