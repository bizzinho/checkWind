from msilib.schema import Error
from time import sleep
import requests
from bs4 import BeautifulSoup as bs
import os
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import pandas as pd
from datetime import datetime as dt
import pathlib
import time

from typing import Union


def pathSetup():
    if len(list(pathlib.Path.cwd().joinpath("driver").glob("*WebDriver*"))) == 1:
        driverPath = pathlib.Path.cwd().joinpath("driver")
    # elif len(pathlib.Path().glob("MicrosoftWebDriver")) > 1:
    # # driverPath = pathlib.Path.cwd().parent.joinpath("driver")
    # driverPath = pathlib.Path(__file__).parent.joinpath("driver")
    os.environ["PATH"] += r";" + str(driverPath)


# TODO: have dictionary of favorite locations so can use name only
def getSoup(id: Union[str, int] = "501145"):
    url = f"https://www.windguru.cz/{id}"
    try:
        driver = webdriver.Edge()
    except WebDriverException:
        pathSetup()
        driver = webdriver.Edge()

    # TODO: don't open a new edge when already one open
    driver.get(url)
    # TODO: only do the soup when page is fully loaded
    time.sleep(3)
    soup = bs(driver.page_source)

    return soup


def parseSoup(soup):
    dates = soup.find_all("tr", id="tabid_0_0_dates")[0]
    today = dt.today()

    forecastDates = [
        (dayHour.text[0:2], int(dayHour.text[2:4]), int(dayHour.text[5:7]))
        for dayHour in dates.find_all("td")
    ]

    firstDate = dt(today.year, today.month, int(forecastDates[0][1]))
    lastDate = firstDate.day
    timestamps = []
    for day in forecastDates:
        if day[1] >= lastDate:
            month = today.month
        else:
            month = today.month + 1
        timestamps.append(dt(today.year, today.month, day[1], day[2]))

    windSpeeds = [
        int(speed.text) for speed in soup.find_all("tr", id="tabid_0_0_WINDSPD")[0]
    ]

    # TODO: formatting of timestamp col and col descriptions?
    df = pd.DataFrame({"Timestamp": timestamps, "Windspeeds": windSpeeds})

    # TODO: different models
