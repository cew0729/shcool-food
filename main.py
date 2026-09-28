import streamlit as st
import requests
import re
import pandas as pd
import plotly.express as px


# ==========================================
# 페이지 설정
# ==========================================

st.set_page_config(
    page_title="우리 학교 메뉴별 급식",
    page_icon="🍚",
    layout="wide"
)


# ==========================================
# 학교 정보
# ==========================================

SCHOOL_NAME = "송탄고등학교"

OFFICE_CODE = "J10"
SCHOOL_CODE = "7530480"

MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# ==========================================
# 조회 기간
# ==========================================

START_DATE = "20250901"
END_DATE = "20260930"


# ==========================================
# 제목
# ==========================================

st.title("우리 학교 메뉴별 급식")

st.write(
    f"{SCHOOL_NAME}의 {START_DATE[:4]}년 {START_DATE[4:6]}월부터 "
    f"{END_DATE[:4]}년 {END_DATE[4:6]}월까지 중식 메뉴를 분석합니다."
)


# ==========================================
# Secrets에서 NEIS 인증키 가져오기
# ==========================================

try:

    NEIS_API_KEY = st.secrets["NEIS_API_KEY"]

except Exception:

    st.error(
        "NEIS_API_KEY를 불러오지 못했습니다. "
        "Streamlit Secrets에 NEIS_API_KEY가 설정되어 있는지 확인해 주세요."
    )

    st.stop()


# ==========================================
# NEIS 급식 데이터 전체 가져오기
# ==========================================

@st.cache_data(ttl=3600)
def get_all_meals():

    all_rows = []

    # 한 번에 가져올 데이터 수
    page_size = 1000

    # 첫 요청
    page_index = 1

    while True:

        params = {
            "KEY": NEIS_API_KEY,
            "Type": "json",
            "pIndex": page_index,
            "pSize": page_size,
            "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
            "SD_SCHUL_CODE": SCHOOL_CODE,
            "MMEAL_SC_CODE": "2",
            "MLSV_FROM_YMD": START_DATE,
            "MLSV_TO_YMD": END_DATE
        }

        response = requests.get(
            MEAL_API,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()


        # ======================================
        # 응답에 급식 정보가 없는 경우
        # ======================================

        if "mealServiceDietInfo" not in data:

            return []


        meal_info = data["mealServiceDietInfo"]


        # ======================================
        # 전체 건수 확인
        # ======================================

        try:

            total_count = int(
                meal_info[0]["head"][1]["list_total_count"]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError
        ):

            total_count = 0


        # ======================================
        # 이번 페이지 데이터
        # ======================================

        try:

            rows = meal_info[1]["row"]

        except (
            KeyError,
            IndexError,
            TypeError
        ):

            rows = []


        all_rows.extend(rows)


        # ======================================
        # 전체 데이터를 모두 가져왔는지 확인
        # ======================================

        if len(all_rows) >= total_count:

            break


        # 다음 페이지
        page_index += 1


        # 안전장치
        if not rows:

            break


    return all_rows


# ==========================================
# 데이터 불러오기
# ==========================================

try:

    rows = get_all_meals()

except requests.RequestException:

    st.error(
        "NEIS 급식 데이터를 가져오는 중 문제가 발생했습니다. "
        "잠시 후 다시 시도해 주세요."
    )

    st.stop()

except Exception as e:

    st.error(
        f"급식 데이터를 불러오지 못했습니다: {e}"
    )

    st.stop()


# ==========================================
# 데이터가 없는 경우
# ==========================================

if not rows:

    st.info(
        "해당 기간에 등록된 중식 데이터가 없습니다."
    )

    st.stop()


# ==========================================
# 데이터프레임 만들기
# ==========================================

df = pd.DataFrame(rows)


# ==========================================
# 필요한 열만 사용
# ==========================================

if "MLSV_YMD" not in df.columns or "DDISH_NM" not in df.columns:

    st.error(
        "급식 응답에서 필요한 데이터를 찾을 수 없습니다."
    )

    st.stop()


df = df[
    [
        "MLSV_YMD",
        "DDISH_NM"
    ]
].copy()


# ==========================================
# 날짜 형식 변환
# ==========================================

df["날짜"] = pd.to_datetime(
    df["MLSV_YMD"],
    format="%Y%m%d",
    errors="coerce"
)


df = df.dropna(
    subset=["날짜"]
)


# ==========================================
# 메뉴 하나씩 분리
# ==========================================

menu_records = []


for _, row in df.iterrows():

    meal_date = row["날짜"]

    menu_text = str(
        row["DDISH_NM"]
    )


    # <br/>, <br>, <BR/> 등 처리
    menu_text = re.sub(
        r"<br\s*/?>",
        "\n",
        menu_text,
        flags=re.IGNORECASE
    )


    # 메뉴를 하나씩 분리
    menu_list = menu_text.split("\n")


    for menu in menu_list:

        menu = menu.strip()


        if not menu:
            continue


        # ==================================
        # 메뉴 뒤의 괄호 속 알레르기 번호 제거
        #
        # 예:
        # 김치찌개(5.6.9)
        # → 김치찌개
        # ==================================

        menu = re.sub(
            r"\s*\([^()]*\)\s*$",
            "",
            menu
        ).strip()


        if not menu:
            continue


        menu_records.append(
            {
                "날짜": meal_date,
                "메뉴": menu
            }
        )


# ==========================================
# 메뉴 데이터가 없는 경우
# ==========================================

if not menu_records:

    st.info(
        "분석할 메뉴 데이터가 없습니다."
    )

    st.stop()


menu_df = pd.DataFrame(
    menu_records
)


# ==========================================
# 같은 날 같은 메뉴가 여러 번 있으면
# 하루 1회로 계산
# ==========================================

menu_df = menu_df.drop_duplicates(
    subset=["날짜", "메뉴"]
)


# ==========================================
# 전체 집계 날짜 수
# ==========================================

counted_days = menu_df["날짜"].nunique()


# ==========================================
# 메뉴별 등장 일수
# ==========================================

menu_count = (
    menu_df
    .groupby("메뉴")["날짜"]
    .nunique()
    .reset_index(name="등장일수")
)


# ==========================================
# 비율 계산
# ==========================================

menu_count["비율"] = (
    menu_count["등장일수"]
    / counted_days
    * 100
)


# ==========================================
# 등장일수 기준 내림차순 정렬
# ==========================================

menu_count = menu_count.sort_values(
    by=["등장일수", "메뉴"],
    ascending=[False, True]
).reset_index(drop=True)


# ==========================================
# 순위
# ==========================================

menu_count["순위"] = (
    menu_count.index + 1
)


# ==========================================
# TOP 10
# ==========================================

top10 = menu_count.head(10).copy()


# ==========================================
# 1위 정보
# ==========================================

first_menu = menu_count.iloc[0]

first_menu_name = first_menu["메뉴"]

first_menu_days = int(
    first_menu["등장일수"]
)

first_menu_ratio = float(
    first_menu["비율"]
)


# ==========================================
# 큰 숫자 카드
# ==========================================

st.markdown("---")

card1, card2, card3 = st.columns(3)


with card1:

    st.metric(
        "집계한 날수",
        f"{counted_days}일"
    )


with card2:

    st.metric(
        "1위 메뉴",
        first_menu_name
    )


with card3:

    st.metric(
        "1위 메뉴 비율",
        f"{first_menu_ratio:.1f}%"
    )


# ==========================================
# 표시할 순위 슬라이더
# ==========================================

st.markdown("---")

max_rank = min(
    10,
    len(menu_count)
)


show_rank = st.slider(
    "몇 위까지 볼까요?",
    min_value=1,
    max_value=max_rank,
    value=max_rank,
    step=1
)


# ==========================================
# 선택한 순위까지 표시
# ==========================================

display_df = menu_count.head(
    show_rank
).copy()


# ==========================================
# 그래프용 순서
# 1위가 맨 위에 오도록 역순
# ==========================================

display_df = display_df.sort_values(
    "등장일수",
    ascending=True
)


# ==========================================
# 가로 막대그래프
# ==========================================

fig = px.bar(
    display_df,
    x="등장일수",
    y="메뉴",
    orientation="h",
    text="등장일수",
    color="등장일수",
    color_continuous_scale="Blues",
    labels={
        "등장일수": "등장한 일수",
        "메뉴": "메뉴"
    },
    hover_data={
        "등장일수": True,
        "비율": ":.1f",
        "메뉴": False
    }
)


fig.update_traces(
    texttemplate="%{text}일",
    textposition="outside"
)


fig.update_layout(
    height=max(
        400,
        show_rank * 55
    ),
    xaxis_title="등장한 일수",
    yaxis_title="메뉴",
    coloraxis_colorbar_title="등장일수",
    margin=dict(
        l=20,
        r=40,
        t=20,
        b=20
    )
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ==========================================
# 메뉴별 상세 정보
# ==========================================

st.markdown("---")

st.markdown("### 메뉴별 등장 일수와 비율")


detail_df = menu_count.head(
    show_rank
).copy()


detail_df["비율"] = detail_df[
    "비율"
].round(1)


detail_df = detail_df[
    [
        "순위",
        "메뉴",
        "등장일수",
        "비율"
    ]
]


detail_df = detail_df.rename(
    columns={
        "순위": "순위",
        "메뉴": "메뉴",
        "등장일수": "등장한 일수",
        "비율": "비율(%)"
    }
)


st.dataframe(
    detail_df,
    use_container_width=True,
    hide_index=True
)
