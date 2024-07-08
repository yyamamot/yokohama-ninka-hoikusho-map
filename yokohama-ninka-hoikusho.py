import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(
    page_title="横浜市認可保育所マップ",
    layout="wide"
)

file_path_enrolled_children = '202407-jidou.csv'
file_path_acceptable_children = '202407-kanou.csv'
file_path_waiting_children = '202407-machi.csv'
file_path_location = '202407-location.csv'

# 入所児童数
enrolled_children_map = {
    "０歳児": "児童０歳児", "１歳児": "児童１歳児", "２歳児": "児童２歳児",
    "３歳児": "児童３歳児", "４歳児": "児童４歳児", "５歳児": "児童５歳児",
    "合計": "児童合計"
}

# 受入可能数
acceptable_children_map = {
    "０歳児": "可能０歳児", "１歳児": "可能１歳児", "２歳児": "可能２歳児",
    "３歳児": "可能３歳児", "４歳児": "可能４歳児", "５歳児": "可能５歳児",
    "合計": "可能合計"
}

# 入所待ち人数
waiting_children_map = {
    "０歳児": "待ち０歳児", "１歳児": "待ち１歳児", "２歳児": "待ち２歳児",
    "３歳児": "待ち３歳児", "４歳児": "待ち４歳児", "５歳児": "待ち５歳児",
    "合計": "待ち合計"
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


def load_and_preprocess_data(file_path, column_map):
    df = pd.read_csv(file_path, skiprows=1, encoding='shift_jis')
    df = df.iloc[:, :-1]  # 最右列を削除(オープンデータの最右に空列が存在)
    df.rename(columns=column_map, inplace=True)
    return df


@st.cache_data
def generate_dataframe(file_path_enrolled, file_path_acceptable, file_path_waiting, file_path_location):
    df_enrolled = load_and_preprocess_data(file_path_enrolled, enrolled_children_map)
    df_acceptable = load_and_preprocess_data(file_path_acceptable, acceptable_children_map)
    df_waiting = load_and_preprocess_data(file_path_waiting, waiting_children_map)
    df_location = pd.read_csv(file_path_location)

    df_merged = pd.merge(df_enrolled, df_acceptable,
                         on=["施設所在区", "標準地域コード", "施設・事業名", "施設番号", "更新日"])
    df_merged = pd.merge(df_merged, df_waiting,
                         on=["施設所在区", "標準地域コード", "施設・事業名", "施設番号", "更新日"])
    df_final = pd.concat([df_merged, df_location], axis=1)
    return df_final


def determine_pop_color(enrolled_children, acceptable_children, waiting_children):
    if enrolled_children == '-' or waiting_children == '-' or acceptable_children == '-':
        return 'gray'
    elif str(waiting_children).isdigit() and int(waiting_children) > 0:
        return 'red'
    elif str(acceptable_children).isdigit() and int(acceptable_children) > 0:
        return 'green'
    return 'red'


def get_column_data(row, column_map, selected_years_old):
    column_name = column_map[selected_years_old]
    return row[column_name]


def main():
    # -----------------------------------------------------------------------------
    # データフレーム作成
    # -----------------------------------------------------------------------------
    df = generate_dataframe(file_path_enrolled_children,
                            file_path_acceptable_children,
                            file_path_waiting_children,
                            file_path_location)

    # -------------------------------------------------------------------------
    # サイドバー: 施設所在区を選択
    # -------------------------------------------------------------------------
    with st.sidebar:
        district_options = [''] + list(df['施設所在区'].unique())
        selected_district = st.sidebar.selectbox(
            '施設所在区を選択してください:',
            options=district_options,
            index=0
        )
        if selected_district != '':
            df = df[df['施設所在区'] == selected_district]

    # -------------------------------------------------------------------------
    # サイドバー: 児童のクラスを選択
    # -------------------------------------------------------------------------
    years_old_list = ['０歳児', '１歳児', '２歳児', '３歳児', '４歳児', '５歳児']
    with st.sidebar:
        years_old_options = [''] + years_old_list
        selected_years_old = st.sidebar.selectbox(
            '児童のクラスを選択してください:',
            options=years_old_options,
            index=0
        )
        if selected_years_old == '':
            selected_years_old = '合計'

    # -------------------------------------------------------------------------
    # ヘッダ表示
    # -------------------------------------------------------------------------
    st.title('横浜市認可保育園マップ(2024/07)')
    st.markdown(
        "- [横浜市オープンデータポータル: 保育所等の入所状況](https://data.city.yokohama.lg.jp/dataset/kodomo_nyusho-jokyo)のデータを基に可視化しています。\n"
        "- サイドバーから施設所在区および児童のクラスを選択してください。\n"
        "- デフォルトでは全区域および全クラスの合計を表示しますので重たいです。施設所在区を選択すると描画が高速になります。")

    # -------------------------------------------------------------------------
    # マップ表示
    # -------------------------------------------------------------------------
    m = folium.Map(
        location=district_map[selected_district],
        attr='openstreetmap',
        zoom_start=14,
    )
    for _, row in df.iterrows():
        if row['緯度'] == 0 or pd.isna(row['緯度']) or row['経度'] == 0 or pd.isna(row['経度']):
            continue

        enrolled = get_column_data(row, enrolled_children_map, selected_years_old)
        acceptable = get_column_data(row, acceptable_children_map, selected_years_old)
        waiting = get_column_data(row, waiting_children_map, selected_years_old)

        pop = f"<span style='font-size: 16px;'>{row['施設・事業名']}</span><br>" \
              f"<span style='font-size: 16px;'>{selected_years_old} " \
              f"入所待ち人数: {waiting} 受入可能数: {acceptable} 入所児童数: {enrolled}</span>"
        folium.Marker(
            location=[row['緯度'], row['経度']],
            tooltip=row['施設・事業名'],
            popup=folium.Popup(pop, max_width=400),
            icon=folium.Icon(icon="home", icon_color="white", color=determine_pop_color(enrolled, acceptable, waiting))
        ).add_to(m)

    page_width = streamlit_js_eval(js_expressions='window.innerWidth', key='WIDTH', want_output=True)
    st_data = st_folium(m, width=page_width)


if __name__ == "__main__":
    main()
