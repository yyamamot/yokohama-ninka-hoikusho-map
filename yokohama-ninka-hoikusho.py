import json
from dataclasses import dataclass, asdict

import folium
import geojson
import polars as pl
import streamlit as st
from geojson import Feature, Point, FeatureCollection
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval


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


config_json = load_config()

# データフレームのカラム名を変換
data_maps = {
    # 入所待ち人数
    'waiting': {
        "０歳児": "待ち０歳児", "１歳児": "待ち１歳児", "２歳児": "待ち２歳児",
        "３歳児": "待ち３歳児", "４歳児": "待ち４歳児", "５歳児": "待ち５歳児",
        "合計": "待ち合計"
    },
    # 受入可能数
    'acceptable': {
        "０歳児": "可能０歳児", "１歳児": "可能１歳児", "２歳児": "可能２歳児",
        "３歳児": "可能３歳児", "４歳児": "可能４歳児", "５歳児": "可能５歳児",
        "合計": "可能合計"
    },
    # 入所児童数
    'enrolled': {
        "０歳児": "児童０歳児", "１歳児": "児童１歳児", "２歳児": "児童２歳児",
        "３歳児": "児童３歳児", "４歳児": "児童４歳児", "５歳児": "児童５歳児",
        "合計": "児童合計"
    },
}

# 施設所在区を選択後の座標
district_map = {
    "": [35.452725, 139.595061],  # 横浜市
    "鶴見区": [35.494365, 139.680332],
    "神奈川区": [35.485009, 139.618465],
    "西区": [35.457168, 139.621194],
    "中区": [35.425549, 139.656855],
    "南区": [35.426215, 139.604756],
    "港南区": [35.392698, 139.581195],
    "保土ケ谷区": [35.464714, 139.576667],
    "旭区": [35.475987, 139.528257],
    "磯子区": [35.391347, 139.616633],
    "金沢区": [35.35158, 139.622406],
    "港北区": [35.526136, 139.620386],
    "緑区": [35.515404, 139.531977],
    "青葉区": [35.560206, 139.517941],
    "戸塚区": [35.402379, 139.530186],
    "栄区": [35.359876, 139.554421],
    "泉区": [35.418646, 139.501889],
    "瀬谷区": [35.469557, 139.488063],
}

district_keys = [
    "", "鶴見区", "神奈川区", "西区", "中区", "南区", "港南区", "保土ケ谷区",
    "旭区", "磯子区", "金沢区", "港北区", "緑区", "青葉区", "戸塚区",
    "栄区", "泉区", "瀬谷区"
]


def preprocess_data(df, column_map):
    df = df[:, :-1]  # 最終列を削除
    df = df.rename(column_map)
    return df


@st.cache_data
def generate_dataframe(config_json, data_maps):
    merge_keys = ["施設所在区", "標準地域コード", "施設・事業名", "施設番号", "更新日"]

    dfs = {}
    for key in ['waiting', 'acceptable', 'enrolled']:
        df = pl.read_csv(config_json[key], skip_rows=1)
        df_preprocessed = preprocess_data(df, data_maps[key])
        dfs[key] = df_preprocessed

    df_location = pl.read_csv(config_json['location']).select(pl.all().exclude('列名'))

    # df_locationのカラム名を変更
    df_location = df_location.rename({"施設・事業名": "施設・事業名_ロケーション"})

    df_merged = dfs['enrolled'].join(dfs['acceptable'], on=merge_keys)
    df_merged = df_merged.join(dfs['waiting'], on=merge_keys)
    return pl.concat([df_merged, df_location], how='horizontal')


def determine_pop_color(enrolled_children, acceptable_children, waiting_children):
    if '-' in [enrolled_children, acceptable_children, waiting_children]:
        return 'gray'
    if str(waiting_children).isdigit() and int(waiting_children) > 0:
        return 'red'
    if str(acceptable_children).isdigit() and int(acceptable_children) > 0:
        return 'green'
    return 'red'


def fetch_age_group_data(row, column_map, age_group):
    column_name = column_map[age_group]
    return str(row[column_name])


def main():
    st.set_page_config(
        page_title="横浜市認可保育所マップ",
        layout="wide"
    )

    # -----------------------------------------------------------------------------
    # データフレーム作成
    # -----------------------------------------------------------------------------
    df = generate_dataframe(config_json, data_maps)

    # -------------------------------------------------------------------------
    # サイドバー: 施設所在区を選択
    # -------------------------------------------------------------------------
    with st.sidebar:
        # デフォルトは横浜市(表示場は空白)
        district_options = district_keys
        selected_district = st.sidebar.selectbox(
            '施設所在区を選択してください:',
            options=district_options,
            index=0
        )
        if selected_district != '':
            df = df.filter(pl.col('施設所在区') == selected_district)

    # -------------------------------------------------------------------------
    # サイドバー: 児童のクラスを選択
    # -------------------------------------------------------------------------
    age_categories = ['０歳児', '１歳児', '２歳児', '３歳児', '４歳児', '５歳児']
    with st.sidebar:
        # デフォルトは合計(表示場は空白)
        age_categories_options = [''] + age_categories
        selected_age = st.sidebar.selectbox(
            '児童のクラスを選択してください:',
            options=age_categories_options,
            index=0
        )
        if selected_age == '':
            selected_age = '合計'

    # -----------------------------------------------------------------------------
    # GeoJSON 作成
    # Note: folium.GeoJson() でフォント設定ができないため、GeoJSON内にHTMLタグを埋め込む
    # -----------------------------------------------------------------------------
    features = []
    for row in df.iter_rows(named=True):
        age_groups = ['０歳児', '１歳児', '２歳児', '３歳児', '４歳児', '５歳児', '合計']
        props = {"施設・事業名": f"<span style='font-size: 16px;'>{row['施設・事業名']}</span>"}

        # GeoJsonのpropertiesに各年齢層のデータを追加
        for age in age_groups:
            waiting_data = fetch_age_group_data(row, data_maps['waiting'], age)
            acceptable_data = fetch_age_group_data(row, data_maps['acceptable'], age)
            enrolled_data = fetch_age_group_data(row, data_maps['enrolled'], age)

            color_style = "color: red;" if age == selected_age else ""
            props[age] = f"<span style='font-size: 16px; {color_style}'>" + \
                         f'待ち: {waiting_data} ' + \
                         f'可能: {acceptable_data} ' + \
                         f'総数: {enrolled_data}' + \
                         "</span>"

            # マーカーの色を保存。GeoJSON表示時に使用
            props[age + '_color'] = determine_pop_color(enrolled_data, acceptable_data, waiting_data)

        features.append(Feature(geometry=Point((row['経度'], row['緯度'])), properties=props))
    yokohama_geojson = geojson.dumps(FeatureCollection(features), ensure_ascii=False)

    # -------------------------------------------------------------------------
    # ヘッダ表示
    # -------------------------------------------------------------------------
    st.markdown(
        f"### 横浜市認可保育所マップ({config_json['last_updated']})\n"
        "- [横浜市オープンデータポータル: 保育所等の入所状況](https://data.city.yokohama.lg.jp/dataset/kodomo_nyusho-jokyo)のデータを基に可視化しています。\n"
        "- サイドバーから施設所在区および児童のクラスを選択してください。")

    # -------------------------------------------------------------------------
    # マップ表示
    # -------------------------------------------------------------------------
    m = folium.Map(
        location=district_map[selected_district],
        attr='openstreetmap',
        zoom_start=14,
    )
    popup_fields = ['施設・事業名', '０歳児', '１歳児', '２歳児', '３歳児', '４歳児', '５歳児', '合計']
    folium.GeoJson(
        yokohama_geojson,
        popup=folium.GeoJsonPopup(
            fields=popup_fields,
            # Note: フォント設定ができないため、aliasでフォントサイズを設定
            aliases=[f"<span style='font-size: 16px;'>{field}</span>" for field in popup_fields],
            localize=True,
            sticky=False,
            labels=True,
        ),
        marker=folium.Marker(icon=folium.Icon(icon='home')),
        style_function=lambda x: {'markerColor': x['properties'][selected_age + '_color']}
    ).add_to(m)

    page_width = streamlit_js_eval(js_expressions='window.innerWidth', key='WIDTH', want_output=True)
    st_data = st_folium(m, width=page_width)


if __name__ == "__main__":
    main()
