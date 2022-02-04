import os
import math
import pandas as pd

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
import requests
from tempfile import mkdtemp
from datetime import datetime
from daylighthours import daylighthours, sidereal_time

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
        timezone = float(request.form.get("timezone"))
        objectType = request.form.get("object")

        sunrise, sunset = daylighthours(latitude, longitude)
        local_sidereal_time_sunset = sidereal_time(sunset, longitude)
        local_sidereal_time_sunrise = sidereal_time(sunrise, longitude)

        # Calculate sunrise and sunset time based on local timezone
        local_sunrise_time = sunrise + timezone
        local_sunset_time = sunset + timezone
        twilight_length = 1 #Assume 1 hour of twilight

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

        return render_template("observingplan.html", index_input=input)

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
        timezone = float(request.form.get("timezone"))
        objectType = "all"
        aperture = float(request.form.get("aperture"))
        telescopefl = float(request.form.get("telescopefl"))
        eyepiecefl = float(request.form.get("eyepiecefl"))
        # eyepiecefov = float(request.form.get("eyepiecefov"))
        sortby = request.form.get("sort")
        nelm = float(request.form.get("nelm"))
        objectType = request.form.get("objectTypes")
        magnification = telescopefl / eyepiecefl
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

        return render_template("observingplanadv.html", index_input=input, telescopefl=telescopefl)