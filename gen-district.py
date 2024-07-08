import time
import xml.etree.ElementTree as ET

import requests

districts = [
    "横浜市",
    "横浜市鶴見区",
    "横浜市神奈川区",
    "横浜市西区",
    "横浜市中区",
    "横浜市南区",
    "横浜市港南区",
    "横浜市保土ケ谷区",
    "横浜市旭区",
    "横浜市磯子区",
    "横浜市金沢区",
    "横浜市港北区",
    "横浜市緑区",
    "横浜市青葉区",
    "横浜市戸塚区",
    "横浜市栄区",
    "横浜市泉区",
    "横浜市瀬谷区",
]


def is_valid_coordinates(lat, lng):
    return (lat is not None and lng is not None) and (lat.text != '0' and lng.text != '0')


def get_lat_lng(url, retry=10):
    attempt = 0
    while attempt < retry:
        response = requests.get(url)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            lat = root.find('.//lat')
            lng = root.find('.//lng')
            if is_valid_coordinates(lat, lng):
                return lat.text, lng.text
        attempt += 1
        time.sleep(11)
    return 0, 0


print("緯度,経度")
for district in districts:
    lat, lng = get_lat_lng(f"https://www.geocoding.jp/api/?q={district}")
    print(f"[{lat},{lng}]")

    time.sleep(11)

'''
緯度,経度
[35.452725,139.595061]
[35.494365,139.680332]
[35.485009,139.618465]
[35.457168,139.621194]
[35.425549,139.656855]
[35.426215,139.604756]
[35.392698,139.581195]
[35.464714,139.576667]
[35.475987,139.528257]
[35.391347,139.616633]
[35.35158,139.622406]
[35.526136,139.620386]
[35.515404,139.531977]
[35.560206,139.517941]
[35.402379,139.530186]
[35.359876,139.554421]
[35.418646,139.501889]
[35.469557,139.488063]
'''
