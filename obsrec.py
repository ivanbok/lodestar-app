import suncalc
import datetime

def timetodecimal(timemin):
    timedec = int(timemin) + float(timemin - int(timemin))/0.6
    return timedec

def timefloattostring(timefloat):
    hours_int = int(timefloat)
    min_str = str(int(60*(timefloat - int(timefloat))))
    if len(min_str) == 1:
        min_str = "0" + min_str
    morning = True
    if hours_int >= 12:
        morning = False
    if hours_int > 12:
        hours_int = hours_int - 12
    if morning:
        outputstr = str(hours_int) + ":" + min_str + " AM"
    else:
        outputstr = str(hours_int) + ":" + min_str + " PM"
    return outputstr

def timedurtostr(timefloat):
    hours_int = int(timefloat)
    min_str = str(int(100*(timefloat - int(timefloat))))
    outputstr = str(hours_int) + "H " + min_str + "min"
    return outputstr

def obsrecommendation(longitude, latitude, time):
    suntimesdict = suncalc.getTimes(time, latitude, longitude)
    nightstart = timetodecimal(float(suntimesdict["night"]))
    nightend = timetodecimal(float(suntimesdict["nightEnd"]))
    moontimesdict = suncalc.getMoonTimes(time, latitude, longitude)
    moonrise = timetodecimal(float(moontimesdict["rise"]))
    moonset = timetodecimal(float(moontimesdict["set"]))
    moonilluminationdict = suncalc.getMoonIllumination(time)
    moonillumination = moonilluminationdict['fraction']

    # Case 1a: Moon Sets after night starts, but before midnight
    if moonset > nightstart and moonset < 24:
        obs_start = moonset
        obs_end = nightend
        obs_duration = nightend + 24 - moonset
        good = True
    # Case 1b: Moon Sets after night starts, but after midnight
    elif moonset < nightend:
        obs_start = moonset
        obs_end = nightend
        obs_duration =  nightend - moonset
        good = True
    # Case 2a: Moon Rises after night starts, but before midnight
    elif moonrise > nightstart and moonrise < 24:
        obs_start = nightstart
        obs_end = moonrise
        obs_duration =  moonrise - nightstart
        good = True
    # Case 2b: Moon Rises after night starts, but after midnight
    elif moonrise < nightend:
        obs_start = nightstart
        obs_end = moonrise
        obs_duration = (24 - nightstart) + moonrise
        good = True
    else: 
        obs_start = nightstart
        obs_end = nightend
        obs_duration = 0
        good = False

    obs_start_str = timefloattostring(obs_start)
    obs_end_str = timefloattostring(obs_end)
    obs_duration_str = timedurtostr(obs_duration)

    if good:
        outputstr = "The best time to observe today is from " + obs_start_str + " to " + obs_end_str + ", which is a total duration of " + obs_duration_str + ". "
    else:
        outputstr = "We do not recommend observing today as the moon is up throughout the night."

    return outputstr

# {'sunriseEnd': '07:21', 'nadir': '01:21', 'goldenHourEnd': '07:47', 'dusk': '19:44', 'nightEnd': '06:07', 'night': '20:34', 'goldenHour': '18:54', 'sunset': '19:23', 'nauticalDawn': '06:32', 'sunsetStart': '19:21', 'solarNoon': '13:21', 'dawn': '06:57', 'nauticalDusk': '20:09', 'sunrise': '07:19'}
# {'rise': '10.36', 'set': '22.57'}
# {'phase': 0.14782412626126656, 'angle': -1.9194394969890207, 'fraction': 0.20060480637856926}

# print(obsrecommendation(longitude, latitude, datetime.datetime.now()))

def getstartendtime(longitude, latitude, time):
    suntimesdict = suncalc.getTimes(time, latitude, longitude)
    nightstart = timetodecimal(float(suntimesdict["night"]))
    nightend = timetodecimal(float(suntimesdict["nightEnd"]))
    moontimesdict = suncalc.getMoonTimes(time, latitude, longitude)
    moonrise = timetodecimal(float(moontimesdict["rise"]))
    moonset = timetodecimal(float(moontimesdict["set"]))

    # Case 1a: Moon Sets after night starts, but before midnight
    if moonset > nightstart and moonset < 24:
        obs_start = moonset
        obs_end = nightend
        obs_duration = nightend + 24 - moonset
        good = True
    # Case 1b: Moon Sets after night starts, but after midnight
    elif moonset < nightend:
        obs_start = moonset
        obs_end = nightend
        obs_duration =  nightend - moonset
        good = True
    # Case 2a: Moon Rises after night starts, but before midnight
    elif moonrise > nightstart and moonrise < 24:
        obs_start = nightstart
        obs_end = moonrise
        obs_duration =  moonrise - nightstart
        good = True
    # Case 2b: Moon Rises after night starts, but after midnight
    elif moonrise < nightend:
        obs_start = nightstart
        obs_end = moonrise
        obs_duration = (24 - nightstart) + moonrise
        good = True
    else: 
        obs_start = nightstart
        obs_end = nightend
        obs_duration = 0
        good = False

    return obs_start, obs_end