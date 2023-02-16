ZURICH_API = "https://tecdottir.herokuapp.com/measurements/"
GURU_URI = "https://www.windguru.cz/"
GURU_INFO = {
    "Wind speed [kn]": "WINDSPD",
    "Wind gusts [kn]": "GUST",
    "Wind direction": "SMER",
    "Temperature [C]": "TMP",
    "Precipitation [mm/h]": "APCP1s",
}

ZH_INFO = {
    "Timestamp": "timestamp_cet",
    "Wind speed [kn]": "wind_speed_avg_10min_kn",
    "Wind gusts [kn]": "wind_gust_max_10min_kn",
    "Wind direction (angle)": "wind_direction",
    "Temperature [C]": "air_temperature",
    "Precipitation [mm/h]": "precipitation",
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
GURU_LOCATIONS = {"zurich": 57016, "costa nova": 501145}
METEO_LOCATIONS = {"fluntern": "SMA"}

METEO_BASE = "https://data.geo.admin.ch/ch.meteoschweiz.messwerte-"
METEO_GUSTS = (
    METEO_BASE
    + "wind-boeenspitze-kmh-10min/ch.meteoschweiz.messwerte-wind-boeenspitze-kmh-10min_de.csv"
)
METEO_SPEED = (
    METEO_BASE
    + "windgeschwindigkeit-kmh-10min/ch.meteoschweiz.messwerte-windgeschwindigkeit-kmh-10min_de.csv"
)
METEO_TEMP = (
    METEO_BASE
    + "lufttemperatur-10min/ch.meteoschweiz.messwerte-lufttemperatur-10min_de.csv"
)

METEO_RAIN = (
    METEO_BASE
    + "niederschlag-10min/ch.meteoschweiz.messwerte-niederschlag-10min_de.csv"
)
