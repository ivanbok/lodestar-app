from daylighthours import daylighthours, sidereal_time

longitude = 103.48
latitude = 1.22
sunrise, sunset = daylighthours(latitude, longitude)

UTC_time = sunset
local_sidereal_time = sidereal_time(UTC_time, longitude)
print(sunrise)