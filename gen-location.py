import csv
import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict

import pandas as pd
import requests


@dataclass
class Config:
    last_updated: str
    waiting: str
    acceptable: str
    enrolled: str
    last_month_location: str
    location: str


def load_config() -> dict:
    with open('config.json', 'r') as file:
        config_dict = json.load(file)
    return asdict(Config(**config_dict))


def is_valid_coordinates(lat, lng):
    return (lat is not None and lng is not None) and (lat.text != '0' and lng.text != '0')


def fetch_lat_lng(url, retry=10):
    attempt = 0
    while attempt < retry:
        time.sleep(10)
        response = requests.get(url)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            lat = root.find('.//lat')
            lng = root.find('.//lng')
            if is_valid_coordinates(lat, lng):
                return lat.text, lng.text
        attempt += 1
    return 0, 0


def load_saved_locations(file_path):
    """
    指定されたCSVファイルから保育園の名前と緯度経度情報を読み込み、
    それらを辞書として返す関数。

    :param file_path: 緯度経度情報が保存されているCSVファイルのパス
    :return: 保育園の名前をキーとし、その緯度と経度をタプルとして格納した辞書
    """
    df = pd.read_csv(file_path, header=None)
    # 保育園の名前をキー、緯度と経度を値とする辞書
    location_dict = {row[0]: (row[1], row[2]) for row in df.itertuples(index=False)}
    return location_dict


if __name__ == "__main__":
    config_json = load_config()
    df_yokohama = pd.read_csv(config_json['waiting'], skiprows=1)
    saved_locations_dict = load_saved_locations(config_json['last_month_location'])

    with open(config_json['location'], mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['施設・事業名', '緯度', '経度'])

        for index, row in df_yokohama.iterrows():
            nursery_house = row['施設・事業名']
            district = row['施設所在区']
            if nursery_house in saved_locations_dict:
                lat, lng = saved_locations_dict[nursery_house]
            else:
                lat, lng = fetch_lat_lng(f"https://www.geocoding.jp/api/?q=横浜市{district} {nursery_house}")
            print(f"{index:04} {nursery_house},{lat},{lng}")
            writer.writerow([nursery_house, lat, lng])
