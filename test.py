import requests

has_url = False
r = requests.get("https://en.wikipedia.org/wiki/NGC_1976")
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

print(imgurl)
# content="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg/1200px-Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg"/>