import csv
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

file_path = '202407-machi.csv'
output_file_path = '202407-location.csv'

df = pd.read_csv(file_path, header=None, skiprows=2, encoding='shift_jis')
district_column = df.iloc[:, 2]


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


with open(output_file_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['緯度', '経度'])

    for district in district_column:
        lat, lng = get_lat_lng(f"https://www.geocoding.jp/api/?q={district}")
        print(f"{district},{lat},{lng}")
        writer.writerow([lat, lng])
        time.sleep(11)
