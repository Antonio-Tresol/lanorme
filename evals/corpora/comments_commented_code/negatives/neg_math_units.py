"""Math/unit annotation comments next to numeric values."""

from __future__ import annotations


def orbit() -> dict:
    altitude = 408_000  # meters above mean sea level
    velocity = 7660  # m/s, approximate ISS orbital speed
    period = 92.68  # minutes per orbit
    # g = 9.80665 m/s^2 at sea level
    # 1 AU = 1.496e11 m
    return {"alt": altitude, "v": velocity, "T": period}


def thermo(t_celsius: float) -> float:
    # t in degrees Celsius; output in Kelvin
    # delta-T per layer ~= 0.5 K
    # heat flux Q = k * A * dT / L  (W/m^2)
    return t_celsius + 273.15


# pi ~= 3.14159265, used for angle conversions below
# tolerance: +/- 1e-6 radians
