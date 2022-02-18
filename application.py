import os
import math
import pandas as pd

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
import requests
from tempfile import mkdtemp
from datetime import datetime, timedelta
from daylighthours import daylighthours, sidereal_time
from bestviewed import bestviewed, monthtostring
import suncalc
import obsrec

# Configure application
app = Flask(__name__, static_url_path="", static_folder="static")

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///dso.db")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/select')
def select():
    return render_template("select.html")

@app.route('/getcoords')
def getcoords():
    return render_template("getcoords.html")

@app.route('/getcoordsg')
def getcoordsg():
    return render_template("getcoordsg.html")

@app.route('/getcoordsn')
def getcoordsn():
    return render_template("getcoordsn.html")

@app.route('/getcoordsoc')
def getcoordsoc():
    return render_template("getcoordsoc.html")

@app.route('/getcoordsgc')
def getcoordsgc():
    return render_template("getcoordsgc.html")

@app.route('/obsplan', methods = ['POST', 'GET'])
def obsplan():
    if request.method == "GET":
        return render_template("getcoords.html")
    else:
        # Configurable inputs
        mag_limit = 14

        latitude = float(request.form.get("latitude"))
        latitude_upper = latitude + 60
        latitude_lower = latitude - 60
        longitude = float(request.form.get("longitude"))
        coordsstr = printcoords(latitude, longitude)
        timezone = float(request.form.get("timezone"))
        objectType = request.form.get("object")

        sunrise, sunset = daylighthours(latitude, longitude)
        local_sidereal_time_sunset = sidereal_time(sunset, longitude)
        local_sidereal_time_sunrise = sidereal_time(sunrise, longitude)

        # Calculate sunrise and sunset time based on local timezone
        local_sunrise_time = sunrise + timezone
        local_sunset_time = sunset + timezone
        twilight_length = 1 #Assume 1 hour of twilight

        # Calculate moonrise and moonset time
        moontimesdict = suncalc.getMoonTimes(datetime.now() + timedelta(hours=8), latitude, longitude)
        if 'rise' in moontimesdict.keys():
            moonrise = obsrec.timetodecimal(float(moontimesdict["rise"]))
            moonrisestr = timefloattostr(moonrise)
        else:
            moonrisestr = "N/A Today"

        if 'set' in moontimesdict.keys():
            moonset = obsrec.timetodecimal(float(moontimesdict["set"]))
            moonsetstr = timefloattostr(moonset)
        else:
            moonsetstr = "N/A Today"
        
        # Calculate the hours of darkness at location
        dark_hours_before_midnight = 24 - local_sunset_time - twilight_length
        dark_hours_after_midnight = local_sunrise_time - twilight_length
        total_dark_hours = dark_hours_before_midnight + dark_hours_after_midnight
        local_midnight = (local_sunset_time + twilight_length + (total_dark_hours / 2)) % 24

        # Find difference between sidereal and clock time:
        sidereal_time_difference = local_sidereal_time_sunset - sunset

        # Extract Database with filter applied on magnitude and latitude limits
        if objectType == "all":
            rows = db.execute("SELECT object, type, con, ra, dec, mag, subr, size_max, size_min FROM dso WHERE mag < :mag_limit AND dec > :latitude_lower AND dec < :latitude_upper AND type <> :onestar",
                mag_limit=mag_limit, latitude_lower=latitude_lower, latitude_upper=latitude_upper, onestar="1STAR")
        else:
            rows = db.execute("SELECT object, type, con, ra, dec, mag, subr, size_max, size_min FROM dso WHERE mag < :mag_limit AND dec > :latitude_lower AND dec < :latitude_upper AND type LIKE :objectType",
                mag_limit=mag_limit, latitude_lower=latitude_lower, latitude_upper=latitude_upper, objectType="%" + objectType + "%")

        # rows['link'] = df.apply(lambda _: '', axis=1)

        index_input = []
        for row in rows:
            object_name = row['object']
            edited_name = ""
            for char in object_name:
                if char == " ":
                    char = "_"
                edited_name = edited_name + char
            link = "https://en.wikipedia.org/wiki/" + edited_name
            # row['link'] = link
            if row['subr'] and row['subr'] < 99:
                surface_brightness = row['subr']
            elif row['size_max'] and row['size_min']:
                ## Computation of surface brightness (assuming rectangular dimensions)
                # Parse max diameter
                size_max = row['size_max'].strip()
                size_max = size_max.split()
                if not size_max:
                    size_max = 1
                else:
                    size_max = size_max[0]
                size_max = float(size_max)
                # Parse min diameter
                size_min = row['size_min'].strip()
                size_min = size_min.split()
                if not size_min:
                    size_min = 1
                else:
                    size_min = size_min[0]
                size_min = float(size_min)
                # Surface area in arcsec
                surface_area = size_max * size_min * 3600
                magnitude_factor = 2.5 * math.log10(surface_area)
                surface_brightness = row['mag'] + magnitude_factor
            else:
                surface_brightness = row['mag']

            object = row['object']
            type = row['type']
            con = row['con']
            hour_angle_at_sunset = local_sidereal_time_sunset - row['ra']
            if row['ra'] > 0:
                ra = '+'+'{:,.2f}'.format(row['ra'])
            else:
                ra = '{:,.2f}'.format(row['ra'])
            if row['dec'] > 0:
                dec = '+'+'{:,.2f}'.format(row['dec'])
            else:
                dec = '{:,.2f}'.format(row['dec'])
            # mag = row['mag']

            if total_dark_hours > 6:
                visibility = (hour_angle_at_sunset > (-12) and hour_angle_at_sunset < 4) or hour_angle_at_sunset > 12 - (total_dark_hours - 6)
            else:
                visibility = hour_angle_at_sunset > (-6 - total_dark_hours) and hour_angle_at_sunset < 4

            if visibility:
                # Calculate Meridian Transit Time
                local_sidereal_time_meridian = row['ra']
                UTC_time_meridian = local_sidereal_time_meridian - sidereal_time_difference
                local_time_meridian = UTC_time_meridian + timezone #Convert to local timezone

                # Split between hours and minutes
                local_time_meridian = local_time_meridian % 24
                if local_time_meridian > local_sunrise_time and local_time_meridian < local_sunrise_time + 6:
                    best_viewed = "Before Sunrise"
                elif local_time_meridian > local_midnight and local_time_meridian < local_sunrise_time + 6:
                    best_viewed = "After Midnight"
                elif local_time_meridian > local_sunset_time + 1:
                    best_viewed = "Before Midnight"
                else:
                    best_viewed = "After Sunset"
                local_time_meridian_hours = int(local_time_meridian)
                local_time_meridian_minutes = int(round((local_time_meridian - local_time_meridian_hours) * 60))
                if local_time_meridian_hours < 10:
                    local_time_meridian_hours = '0' + str(local_time_meridian_hours)
                else:
                    local_time_meridian_hours = str(local_time_meridian_hours)
                if local_time_meridian_minutes < 10:
                    local_time_meridian_minutes = '0' + str(local_time_meridian_minutes)
                else:
                    local_time_meridian_minutes = str(local_time_meridian_minutes)

                ## Direction in the sky
                if row['dec'] - latitude > 0:
                    direction = "North"
                    max_altitude = str(round(90 - (row['dec'] - latitude)))
                else:
                    direction = "South"
                    max_altitude = str(round(90 - math.fabs(row['dec'] - latitude)))
                max_altitude = max_altitude + '°'
                local_time_meridian = local_time_meridian_hours + ':' + local_time_meridian_minutes + 'H'
                if surface_brightness < 22:
                    surface_brightness_str = '{:,.2f}'.format(surface_brightness)
                    index_input.append({'object': object, 'link': link, 'type': type, 'con': con, 'transit_time': local_time_meridian, 'best_viewed': best_viewed, 'direction': direction, 'max_altitude': max_altitude,'ra': ra, 'dec': dec, 'surface_brightness': surface_brightness_str, 'surface_brightness_val': float(surface_brightness_str)})

        df = pd.DataFrame(index_input)
        df.sort_values('surface_brightness_val', inplace=True)
        input = df.to_dict('records')

        local_sunrise_time_formatted = timefloattostr(local_sunrise_time)
        local_sunset_time_formatted = timefloattostr(local_sunset_time)
        recommendation = obsrec.obsrecommendation(longitude, latitude, datetime.now())

        return render_template("observingplan.html", index_input=input, coordsstr=coordsstr, local_sunrise_time=local_sunrise_time_formatted, local_sunset_time=local_sunset_time_formatted, moonrise=moonrisestr, moonset=moonsetstr, recommendation=recommendation)

@app.route('/advanced', methods = ['POST', 'GET'])
def advanced():
    if request.method == "GET":
        return render_template("advanced.html")
    else:
        aperture = request.form.get("aperture")
        telescopefl = request.form.get("telescopefl")
        eyepiecefl = request.form.get("eyepiecefl")
        eyepiecefov = request.form.get("eyepiecefov")
        sort = request.form.get("sort")
        nelm = request.form.get("nelm")
        objectTypes = request.form.get("objectTypes")
        return render_template("getcoordsadv.html", aperture=aperture, telescopefl=telescopefl, eyepiecefl=eyepiecefl, eyepiecefov=eyepiecefov, sort=sort, nelm=nelm, objectTypes=objectTypes)

@app.route('/obsplanadv', methods = ['POST', 'GET'])
def obsplanadv():
    if request.method == "GET":
        return render_template("advanced.html")
    else:
        # Configurable inputs
        #mag_limit = 7

        latitude = float(request.form.get("latitude"))
        latitude_upper = latitude + 60
        latitude_lower = latitude - 60
        longitude = float(request.form.get("longitude"))
        coordsstr = printcoords(latitude, longitude)
        timezone = float(request.form.get("timezone"))
        objectType = "all"
        aperturestr = request.form.get("aperture")
        aperture = float(request.form.get("aperture"))
        telescopefl = float(request.form.get("telescopefl"))
        eyepiecefl = float(request.form.get("eyepiecefl"))
        # eyepiecefov = float(request.form.get("eyepiecefov"))
        sortby = request.form.get("sort")
        nelm = float(request.form.get("nelm"))
        objectType = request.form.get("objectTypes")
        magnification = telescopefl / eyepiecefl
        magnificationstr = str(int(magnification)) + "x"
        # tfov_degrees = eyepiecefov / magnification
        # tfov_arcmin = tfov_degrees * 60
        # tfov_tenth = tfov_arcmin / 10 # One Tenth of TFOV as minimum size required
        # mag_limit = 8.8 + (5 * (math.log10(aperture / 25.4)))
        power_per_inch = magnification / (aperture/25.4)
        mag_limit = nelm + 3 * (math.log10(aperture / 7)) + 2 * (math.log10(power_per_inch))
        # https://www.cloudynights.com/topic/693878-beat-a-dead-horse-calculate-limiting-magnitude-for-my-telescope/

        sunrise, sunset = daylighthours(latitude, longitude)
        local_sidereal_time_sunset = sidereal_time(sunset, longitude)
        local_sidereal_time_sunrise = sidereal_time(sunrise, longitude)

        # Calculate sunrise and sunset time based on local timezone
        local_sunrise_time = sunrise + timezone
        local_sunset_time = sunset + timezone
        twilight_length = 1 #Assume 1 hour of twilight

        # Calculate moonrise and moonset time
        moontimesdict = suncalc.getMoonTimes(datetime.now(), latitude, longitude)
        if 'rise' in moontimesdict.keys():
            moonrise = obsrec.timetodecimal(float(moontimesdict["rise"]))
            moonrisestr = timefloattostr(moonrise)
        else:
            moonrisestr = "N/A Today"

        if 'set' in moontimesdict.keys():
            moonset = obsrec.timetodecimal(float(moontimesdict["set"]))
            moonsetstr = timefloattostr(moonset)
        else:
            moonsetstr = "N/A Today"

        # Calculate the hours of darkness at location
        dark_hours_before_midnight = 24 - local_sunset_time - twilight_length
        dark_hours_after_midnight = local_sunrise_time - twilight_length
        total_dark_hours = dark_hours_before_midnight + dark_hours_after_midnight
        local_midnight = (local_sunset_time + twilight_length + (total_dark_hours / 2)) % 24

        # Find difference between sidereal and clock time:
        sidereal_time_difference = local_sidereal_time_sunset - sunset

        # Extract Database with filter applied on magnitude and latitude limits
        if objectType == "all":
            rows = db.execute("SELECT object, type, con, ra, dec, mag, subr, size_max, size_min FROM dso WHERE mag < :mag_limit AND dec > :latitude_lower AND dec < :latitude_upper AND type <> :onestar",
                mag_limit=mag_limit, latitude_lower=latitude_lower, latitude_upper=latitude_upper, onestar="1STAR")
        else:
            rows = db.execute("SELECT object, type, con, ra, dec, mag, subr, size_max, size_min FROM dso WHERE mag < :mag_limit AND dec > :latitude_lower AND dec < :latitude_upper AND type LIKE :objectType",
                mag_limit=mag_limit, latitude_lower=latitude_lower, latitude_upper=latitude_upper, objectType="%" + objectType + "%")

        # rows['link'] = df.apply(lambda _: '', axis=1)

        index_input = []
        for row in rows:
            object_name = row['object']
            edited_name = ""
            for char in object_name:
                if char == " ":
                    char = "_"
                edited_name = edited_name + char
            link = "https://en.wikipedia.org/wiki/" + edited_name
            # row['link'] = link
            if row['subr'] and row['subr'] < 99:
                surface_brightness = row['subr']
            elif row['size_max'] and row['size_min']:
                ## Computation of surface brightness (assuming rectangular dimensions)
                # Parse max diameter
                size_max = row['size_max'].strip()
                size_max = size_max.split()
                if not size_max:
                    size_max = 1
                else:
                    size_max = size_max[0]
                size_max = float(size_max)
                # Parse min diameter
                size_min = row['size_min'].strip()
                size_min = size_min.split()
                if not size_min:
                    size_min = 1
                else:
                    size_min = size_min[0]
                size_min = float(size_min)
                # Surface area in arcsec
                surface_area = size_max * size_min * 3600
                magnitude_factor = 2.5 * math.log10(surface_area)
                surface_brightness = row['mag'] + magnitude_factor
            else:
                surface_brightness = row['mag']

            object = row['object']
            type = row['type']
            con = row['con']
            hour_angle_at_sunset = local_sidereal_time_sunset - row['ra']
            if row['ra'] > 0:
                ra = '+'+'{:,.2f}'.format(row['ra'])
            else:
                ra = '{:,.2f}'.format(row['ra'])
            if row['dec'] > 0:
                dec = '+'+'{:,.2f}'.format(row['dec'])
            else:
                dec = '{:,.2f}'.format(row['dec'])
            # mag = row['mag']

            if total_dark_hours > 6:
                visibility = (hour_angle_at_sunset > (-12) and hour_angle_at_sunset < 4) or hour_angle_at_sunset > 12 - (total_dark_hours - 6)
            else:
                visibility = hour_angle_at_sunset > (-6 - total_dark_hours) and hour_angle_at_sunset < 4

            if visibility:
                # Calculate Meridian Transit Time
                local_sidereal_time_meridian = row['ra']
                UTC_time_meridian = local_sidereal_time_meridian - sidereal_time_difference
                local_time_meridian = UTC_time_meridian + timezone #Convert to local timezone

                # Split between hours and minutes
                local_time_meridian = local_time_meridian % 24
                if local_time_meridian > local_sunrise_time and local_time_meridian < local_sunrise_time + 6:
                    best_viewed = "Before Sunrise"
                elif local_time_meridian > local_midnight and local_time_meridian < local_sunrise_time + 6:
                    best_viewed = "After Midnight"
                elif local_time_meridian > local_sunset_time + 1:
                    best_viewed = "Before Midnight"
                else:
                    best_viewed = "After Sunset"
                local_time_meridian_hours = int(local_time_meridian)
                local_time_meridian_minutes = int(round((local_time_meridian - local_time_meridian_hours) * 60))
                if local_time_meridian_hours < 10:
                    local_time_meridian_hours = '0' + str(local_time_meridian_hours)
                else:
                    local_time_meridian_hours = str(local_time_meridian_hours)
                if local_time_meridian_minutes < 10:
                    local_time_meridian_minutes = '0' + str(local_time_meridian_minutes)
                else:
                    local_time_meridian_minutes = str(local_time_meridian_minutes)

                ## Direction in the sky
                if row['dec'] - latitude > 0:
                    direction = "North"
                    max_altitude = str(round(90 - (row['dec'] - latitude)))
                else:
                    direction = "South"
                    max_altitude = str(round(90 - math.fabs(row['dec'] - latitude)))
                max_altitude = max_altitude + '°'
                local_time_meridian = local_time_meridian_hours + ':' + local_time_meridian_minutes + 'H'
                if surface_brightness < mag_limit:
                    surface_brightness_str = '{:,.2f}'.format(surface_brightness)
                    index_input.append({'object': object, 'link': link, 'type': type, 'con': con, 'transit_time': local_time_meridian, 'best_viewed': best_viewed, 'direction': direction, 'max_altitude': max_altitude,'ra': ra, 'dec': dec, 'surface_brightness': surface_brightness_str, 'surface_brightness_val': float(surface_brightness_str)})

        df = pd.DataFrame(index_input)
        df.sort_values(sortby, inplace=True)
        input = df.to_dict('records')

        local_sunrise_time_formatted = timefloattostr(local_sunrise_time)
        local_sunset_time_formatted = timefloattostr(local_sunset_time)
        recommendation = obsrec.obsrecommendation(longitude, latitude, datetime.now())
        equipmentmessage = "This is what you can see with a " + aperturestr + "mm telescope and a magnification of " + magnificationstr + ". "

        return render_template("observingplanadv.html", index_input=input, telescopefl=telescopefl, aperture=aperturestr, magnification=magnificationstr, coordsstr=coordsstr, local_sunrise_time=local_sunrise_time_formatted, local_sunset_time=local_sunset_time_formatted, moonrise=moonrisestr, moonset=moonsetstr, recommendation=recommendation, equipmentmessage=equipmentmessage)

@app.route('/objectsearch', methods = ['POST', 'GET'])
def objectsearch():
    if request.method == "GET":
        return render_template("objectsearch.html")
    else:
        object_name = request.form.get("object")
        searchtype = request.form.get("searchtype")
        latitude = float(request.form.get("latitude"))
        longitude = float(request.form.get("longitude"))
        timezone = float(request.form.get("timezone"))

        sunrise, sunset = daylighthours(latitude, longitude)
        local_sidereal_time_sunset = sidereal_time(sunset, longitude)
        local_sidereal_time_sunrise = sidereal_time(sunrise, longitude)

        # Find difference between sidereal and clock time:
        sidereal_time_difference = local_sidereal_time_sunset - sunset

        # Temporary Translator for Common Options
        if object_name.lower() == "orion nebula":
            object_name = "NGC 1976"
        elif object_name.lower() == "tarantula nebula":
            object_name = "NGC 2070"
        elif object_name.lower() == "helix nebula":
            object_name = "NGC 7293"
        elif object_name.lower() == "omega centauri":
            object_name = "NGC 5139"
        elif object_name.lower() == "centaurus a":
            object_name = "NGC 5128"
        elif object_name.lower() == "veil nebula":
            object_name = "NGC 6960"
        elif object_name.lower() == "rosette nebula":
            object_name = "NGC 2244"
        elif object_name.lower() == "lagoon nebula":
            object_name = "NGC 6523"
        elif object_name.lower() == "north america nebula":
            object_name = "NGC 7000"

        if searchtype == "exact":
            rows = db.execute("SELECT object, type, con, ra, dec, mag, subr, size_max, size_min FROM dso WHERE object LIKE :object",
                object=object_name + "%")
            if len(rows) == 0:
                message = "No matching object was found. Please try another object"
                link = "/objectsearch"
                buttondesc = "Search again"
                return render_template("error.html", message=message, link=link, buttondesc=buttondesc)
            result = rows[0]
            objectType = result["type"]
            ra = float(result["ra"])
            dec = float(result["dec"])
            object_name = result["object"]
            #BRTNB, SNREM, GALXY, CL+NB, GLOCL, OPNCL
            if objectType == "PLNNB":
                objectTypeName = "Planetary Nebula"
                filename = "img/planetarynebula.jpeg"
                objectDescription = object_name + " is a planetary nebula (PN, plural PNe), which is a type of emission nebula consisting of an expanding, glowing shell of ionized gas ejected from red giant stars late in their lives. "
            elif objectType == "BRTNB" or objectType == "CL+NB" or objectType == "LMCCN":
                objectTypeName = "Nebula"
                filename = "img/nebula.jpeg"
                objectDescription = object_name + " is nebula, which is a distinct body of interstellar clouds (which can consist of cosmic dust, hydrogen, helium, molecular clouds; possibly as ionized gases)."
            elif objectType == "SNREM":
                objectTypeName = "Supernova Remnant"
                filename = "img/supernovaremnant.jpeg"
                objectDescription = object_name + " is a supernova remnant, which is the structure resulting from the explosion of a star in a supernova. The supernova remnant is bounded by an expanding shock wave, and consists of ejected material expanding from the explosion, and the interstellar material it sweeps up and shocks along the way. "
            elif objectType == "GALXY":
                objectTypeName = "Galaxy"
                filename = "img/galaxy.jpeg"
                objectDescription = object_name + " is a galaxy, which is a gravitationally bound system of stars, stellar remnants, interstellar gas, dust, and dark matter. The word is derived from the Greek galaxias, literally 'milky', a reference to the Milky Way galaxy that contains the Solar System. "
            elif objectType == "GLOCL":
                objectTypeName = "Globular Cluster"
                filename = "img/globularcluster.jpeg"
                objectDescription = object_name + " is a globular cluster, which is a spherical collection of stars. Globular clusters are very tightly bound by gravity, with a high concentration of stars towards their centers. Their name is derived from Latin globulus—a small sphere. Globular clusters are occasionally known simply as globulars. "
            elif objectType == "OPNCL":
                objectTypeName = "Open Cluster"
                filename = "img/opencluster.jpeg"
                objectDescription = object_name + " is an open cluster, which is a type of star cluster made of up to a few thousand stars that were formed from the same giant molecular cloud and have roughly the same age. More than 1,100 open clusters have been discovered within the Milky Way Galaxy, and many more are thought to exist."
            else:
                objectTypeName = "Unknown Object Type"
                filename = "img/nebula.jpeg"
                objectDescription = object_name + " is object of undefined class."
            
            object_name_url = ""
            for object_namr_char in object_name:
                if object_namr_char == " ":
                    object_name_url = object_name_url + "_"
                else:
                    object_name_url = object_name_url + object_namr_char

            has_url = False
            r = requests.get("https://en.wikipedia.org/wiki/" + object_name_url)
            response = r.text
            if "https://upload.wikimedia.org/wikipedia" in response:
                index = response.index("https://upload.wikimedia.org/wikipedia")
                has_url = True

            loop = has_url
            imgurl = ""
            while loop:
                imgurl = imgurl + response[index]
                index = index + 1
                if response[index] + response[index + 1] + response[index + 2] == "\"/>":
                    loop = False
            
            if has_url:
                filename = imgurl

            max_altitude = 90 - math.fabs(dec - latitude)
            max_altitudestr = str(round(90 - math.fabs(dec - latitude)))
            bestmonth = bestviewed(ra,dec,latitude,longitude)
            if max_altitude > 30:
                startmonth = bestmonth - 2
                endmonth = bestmonth + 2
            else:
                startmonth = bestmonth - 1
                endmonth = bestmonth + 1
            if startmonth < 1:
                startmonth = startmonth + 12
            startmonth = monthtostring(int(startmonth))
            if endmonth > 12:
                endmonth = endmonth - 12
            endmonth_int = endmonth
            startmonth_int = startmonth
            endmonth = monthtostring(int(endmonth))
            bestmonth = monthtostring(int(bestmonth))
            if max_altitude > 60:
                recommendation = object_name + " is best viewed in " + bestmonth + " when it rises to an elevation of " + max_altitudestr + " degrees. "
                recommendation = recommendation + "This means that your current location is an excellent position to view this object as it rises high into the sky. "
                recommendation = recommendation + "It can be seen from your location between the months of " + startmonth + " and " + endmonth + ". "
            elif max_altitude > 30 and max_altitude < 60:
                recommendation = object_name + " is best viewed in " + bestmonth + " when it rises to an elevation of " + max_altitudestr + " degrees. "
                recommendation = recommendation + "It can be seen from your location between the months of " + startmonth + " and " + endmonth + ". "
            elif max_altitude < 30 and max_altitude > 10:
                recommendation = object_name + " is best viewed in " + bestmonth + " when it rises to an elevation of " + max_altitudestr + " degrees. "
                recommendation = recommendation + "Since this object rises to a rather low elevation of " + max_altitudestr + " degrees, it is slightly more challenging to observe from your location. "
                recommendation = recommendation + "As such, we only recommend viewing it between the months of " + startmonth + " and " + endmonth + ". "
            else:
                recommendation = object_name + " is best viewed in " + bestmonth + " when it rises to an elevation of " + max_altitudestr + " degrees. "
                recommendation = recommendation + "However, since this object only rises to a low elevation of " + max_altitudestr + " degrees, it is unlikely to be visible from your location. "

            # Give additional recommendations if object is visible now. 
            objectVisible = False
            sunrise_local = sunrise + timezone
            sunset_local = sunset + timezone
            UTC_time_meridian = ra - sidereal_time_difference
            local_time_meridian = UTC_time_meridian + timezone #Convert to local timezone
            local_time_meridian = local_time_meridian % 24

            if local_time_meridian > sunset_local and local_time_meridian < 24:
                objectVisible = True
            elif local_time_meridian < sunrise_local and local_time_meridian > 0:
                objectVisible = True
            
            if objectVisible and max_altitude > 10:
                transit_time = timefloattostr(local_time_meridian)
                recommendation = recommendation + "The best time to view this object today will be at " + transit_time + " when it will be at its highest point in the sky. "

            ra = float(int(ra * 100))/100
            dec = float(int(dec * 100))/100
            return render_template("objectdetails.html", filename=filename, ra=ra, dec=dec, object_name=object_name, objectTypeName=objectTypeName, objectDescription=objectDescription, recommendation=recommendation, timezone=timezone, local_time_meridian=local_time_meridian)
        else:
            rows = db.execute("SELECT object, type, con, ra, dec, mag, subr, size_max, size_min FROM dso WHERE object LIKE :object",
                object="%" + object_name + "%")
            return render_template("searchresults.html")

def timefloattostr(timefloat):
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

def printcoords(latitude, longitude):
    if latitude > 0:
        latdir = "N"
    else:
        latitude = latitude * -1
        latdir = "S"
    if longitude > 0:
        longdir = "E"
    else:
        longitude = longitude * -1
        longdir = "W"
    latitudestr = str(float(int(latitude * 100))/100)
    longitudestr = str(float(int(longitude * 100))/100)
    coordsstr = latitudestr + " " + latdir + ", " + longitudestr + " " + longdir
    return coordsstr