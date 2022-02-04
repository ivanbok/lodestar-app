from datetime import datetime
import math

def daylighthours(latitude, longitude):
    ## Reference: https://www.esrl.noaa.gov/gmd/grad/solcalc/solareqns.PDF
    latitude = latitude * math.pi / 180
    longitude = longitude * math.pi / 180
    system_time = datetime.now()

    day_of_year = datetime.now().timetuple().tm_yday

    current_year = system_time.year

    if (current_year % 4) == 0:
        leap_year = True
        year_length = 366
    else:
        leap_year = False
        year_length = 365

    # Calculate Fractional Year
    gamma = ((math.pi) / year_length) * (day_of_year - 0.5)

    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) \
    - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))

    decl = 0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(2 * gamma) \
    + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)

    ha = math.acos( ((math.cos(1.585335)) / ((math.cos(latitude)) * math.cos(decl))) \
    - ((math.tan(latitude)) * (math.tan(decl))) )

    sunrise = 720 - 4 * (longitude + ha) * 180 / math.pi - eqtime
    sunset = 720 - 4 * (longitude - ha) * 180 / math.pi - eqtime

    ## Convert to hours (in GMT +0.00)
    sunrise = sunrise / 60
    sunset = sunset / 60

    sunrise_sg = sunrise / 60 + 8
    sunset_sg = sunset / 60 + 8
    return sunrise, sunset

def sidereal_time(UTC_time, longitude):
    ## This function converts clock time to local sidereal time
    ## Reference: https://www.aa.quae.nl/en/reken/sterrentijd.html
    L0 = 99.9678 #in Degrees
    L1 = 360.98565 #in Degrees
    L2 = 2.907879 * (10 ** -13)
    L3 = -5.302 * (10 ** -22)

    system_time = datetime.now()
    day_of_year = datetime.now().timetuple().tm_yday
    current_year = system_time.year

    JD = 0
    for year in range(current_year - 2000 -1):
        if (year % 4) == 0:
            year_length = 366
        else:
            year_length = 365
        JD = JD + year_length
    JD = JD + day_of_year + (UTC_time / 24)

    theta = L0 + (L1 * JD) + (L2 * (JD ** 2)) + (L3 * (JD ** 3)) + longitude
    theta = theta % 360
    local_sidereal_time = theta / 15
    return local_sidereal_time