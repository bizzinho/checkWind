import numpy as np


def beaufortConversion(speed_kn, reverse=False):

    limits = [0, 3, 6, 10, 16, 21, 27, 33, 40, 47, 55, 63]

    if reverse:
        return limits[speed_kn]
    else:
        return next((i for i, e in enumerate(limits) if speed_kn <= e))


def angleToDirection(angle, reverse=False):
    # TODO: if angle is str check if can be cast to numeric, else do reverse?
    limits = np.arange(11.25, 360, 22.5)
    directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]

    if reverse:
        upper = limits[directions.index(angle)]

        return upper - 11.25

    else:
        return next(
            (dir for dir, lims in zip(directions, limits) if angle <= lims), "N"
        )


speedUnits = {
    "from": dict(
        kn=lambda x: x,
        ms=lambda x: x * 0.514,
        kph=lambda x: x * 1.852,
        bf=beaufortConversion,
    ),
    "to": dict(
        kn=lambda x: x,
        ms=lambda x: x / 0.514,
        kph=lambda x: x / 1.852,
        bf=beaufortConversion,
    ),
}
