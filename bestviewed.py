import suncalc
import datetime

def bestviewed(ra,dec,latitude,longitude):
    daysfromautumnalequinox = (float(ra)/24) * 365
    if daysfromautumnalequinox < 99:
        dayofyear = int(daysfromautumnalequinox + 266)
    else:
        dayofyear = int(daysfromautumnalequinox - 99)
    month = int(dayofyear/30.41) + 1
    startview = month - 2
    endview = month + 2
    return month

def monthtostring(month):
    if month == 1:
        monthstr = "January"
    elif month == 2:
        monthstr = "February"
    elif month == 3:
        monthstr = "March"
    elif month == 4:
        monthstr = "April"
    elif month == 5:
        monthstr = "May"
    elif month == 6:
        monthstr = "June"
    elif month == 7:
        monthstr = "July"
    elif month == 8:
        monthstr = "August"
    elif month == 9:
        monthstr = "September"
    elif month == 10:
        monthstr = "October"
    elif month == 11:
        monthstr = "November"
    else:
        monthstr = "December"
    return monthstr
