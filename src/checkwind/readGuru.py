from msilib.schema import Error
from bs4 import BeautifulSoup as bs
import os
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime as dt
import pathlib
import re

from typing import Union

GURU_URI = "https://www.windguru.cz/"
GURU_INFO = {
    "Wind speed [kn]": "WINDSPD",
    "Wind gusts [kn]": "GUST",
    "Wind direction": "SMER",
    "Temperature [C]": "TMP",
    "Precipitation [mm/h]": "APCP1s",
}

NUMERIC_INFO = ["WINDSPD", "GUST", "TMP", "APCP1s", "Wind direction (angle)"]

GURU_MODELS = (
    "WG",
    "GFS-13",
    "AROME-1.3",
    "AROME-2.5",
    "ICON-2.2",
    "Zephr-HD",
    "WRF-9",
    "HARMONIE-5",
    "ICON-7",
    "ICON-13",
    "GDPS-15",
)
GURU_LOCATIONS = {"Zurich": 57016, "Costa Nova": 501145}

# TODO:
# extract actuals (historic?)
# check that model is in GURU models; error handling if page not fully loaded yet
# plot comparison of different models
# query actual values from meteoswiss
# headless


class WindInfo:
    def __init__(self, location="Zurich", headless=True):

        if location in GURU_LOCATIONS.keys():
            self.location = location
        else:
            raise ValueError(f"Location {location} is unknown.")

        try:
            driver = webdriver.Edge()
        except WebDriverException:
            self._pathSetup()
            # if headless:
            #     opt = webdriver.
            #     opt.add_argument("--headless")
            driver = webdriver.Edge()
        driver.implicitly_wait(10)

        self.driver = driver
        self.forecast = dict()
        self.soup = dict()

    def _pathSetup(self):
        if len(list(pathlib.Path.cwd().joinpath("driver").glob("*WebDriver*"))) == 1:
            driverPath = pathlib.Path.cwd().joinpath("driver")
        # elif len(pathlib.Path().glob("MicrosoftWebDriver")) > 1:
        # # driverPath = pathlib.Path.cwd().parent.joinpath("driver")
        # driverPath = pathlib.Path(__file__).parent.joinpath("driver")
        os.environ["PATH"] += r";" + str(driverPath)

    # TODO: have dictionary of favorite locations so can use name only
    def _getSoup(self):

        location = self.location
        id = GURU_LOCATIONS[location]

        url = GURU_URI + str(id)
        self.driver.get(url)

        element_present = EC.presence_of_element_located((By.ID, "tabid_0_0_dates"))
        WebDriverWait(self.driver, 20).until(element_present)

        self.soup = {location: bs(self.driver.page_source)}

    def _getTabId(self, model):
        if self.location not in self.soup.keys():
            self._getSoup()

        legends = self.soup[self.location].find_all("div", {"class": "nadlegend"})

        legendIndex = [
            i for i, leg in enumerate(legends) if bool(re.search(model, leg.text))
        ][0]

        return legends[legendIndex].parent.parent.attrs["data-id"]

    def _parseSoup(self, model="WG"):

        if self.location not in self.soup.keys():
            self._getSoup()

        soup = self.soup[self.location]
        tabid = self._getTabId(model)

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

                descriptions, angles = zip(
                    *[
                        re.sub(r"(\w{1,3}) \((\d{1,3})[.]?.*", r"\1 \2", d).split()
                        for d in directions
                    ]
                )

                myData["Wind direction (description)"] = descriptions
                myData["Wind direction (angle)"] = angles

        # TODO: formatting of timestamp col and col descriptions?
        df = pd.DataFrame(myData)

        df[NUMERIC_INFO] = (
            df[NUMERIC_INFO].apply(pd.to_numeric, errors="coerce").fillna(0)
        )
        df = df.rename(columns=dict(zip(GURU_INFO.values(), GURU_INFO.keys())))

        self.forecast[self.location] = df
