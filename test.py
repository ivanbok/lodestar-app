import suncalc
import datetime

longitude = 103.48
latitude = 1.22

ra = 18.8
dec = 45.67

def bestviewed(ra,dec,latitude,longitude)
    daysfromvernalequinox = (float(ra)/24) * 365
    if daysfromvernalequinox < 286:
        dayofyear = int(daysfromvernalequinox + 79)
    else:
        dayofyear = int(daysfromvernalequinox - 286)
    month = int(dayofyear/30.41) + 1
    startview = month - 2
    endview = month + 2
    return month