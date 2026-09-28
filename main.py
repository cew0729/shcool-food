import streamlit as st
import requests
import re
import pandas as pd
import plotly.express as px
from datetime import date


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
# 제목
# ==========================================

st.title("우리 학교 메뉴별 급식")

st.write(
    "송탄고등학교의 기간별 중식 메뉴를 분석합니다."
)


# ==========================================
# NEIS 인증키 가져오기
# ==========================================

if "NEIS_API_KEY" not in st.secrets:

    st.error(
        "NEIS_API_KEY가 Streamlit Secrets에 없습니다."
    )

    st.stop()


NEIS_API_KEY = st.secrets["NEIS_API_KEY"]


# ==========================================
# 조회 기간
# ==========================================

st.markdown("### 조회 기간")

start_col, end_col = st.columns(2)


with start_col:

    start_date = st.date_input(
        "시작 날짜",
        value=date(2025, 9, 1),
        min_value=date(2025, 1, 1),
        max_value=date(2026, 12, 31)
    )


with end_col:

    end_date = st.date_input(
        "종료 날짜",
        value=date(2026, 9, 30),
        min_value=date(2025, 1, 1),
        max_value=date(2026, 12, 31)
    )


# ==========================================
# 날짜 오류 확인
# ==========================================

if start_date > end_date:

    st.error(
        "시작 날짜가 종료 날짜보다 늦을 수 없습니다."
    )

    st.stop()


# ==========================================
# 조회 기간 표시
# ==========================================

st.info(
    f"현재 조회 기간: "
    f"{start_date.strftime('%Y년 %m월 %d일')} ~ "
    f"{end_date.strftime('%Y년 %m월 %d일')} "
    f"· 중식"
)


# ==========================================
# 날짜 문자열
# ==========================================

start_ymd = start_date.strftime(
    "%Y%m%d"
)

end_ymd = end_date.strftime(
    "%Y%m%d"
)


# ==========================================
# NEIS 전체 급식 데이터 가져오기
# ==========================================

@st.cache_data(ttl=3600)
def get_all_meals(
    api_key,
    start_ymd,
    end_ymd
):

    all_rows = []

    page_size = 1000
    page_index = 1

    total_count = None


    while True:

        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": page_index,
            "pSize": page_size,
            "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
            "SD_SCHUL_CODE": SCHOOL_CODE,
            "MMEAL_SC_CODE": "2",
            "MLSV_FROM_YMD": start_ymd,
            "MLSV_TO_YMD": end_ymd
        }


        response = requests.get(
            MEAL_API,
            params=params,
            timeout=30
        )


        response.raise_for_status()


        data = response.json()


        # ======================================
        # NEIS 오류 확인
        # ======================================

        if "RESULT" in data:

            result = data["RESULT"]

            code = result.get(
                "CODE",
                ""
            )

            message = result.get(
                "MESSAGE",
                ""
            )

            if code != "INFO-000":

                return [], f"{code}: {message}"


        # ======================================
        # 급식 데이터 확인
        # ======================================

        if "mealServiceDietInfo" not in data:

            return [], "급식 데이터가 없습니다."


        meal_info = data[
            "mealServiceDietInfo"
        ]


        # ======================================
        # 전체 건수 확인
        # ======================================

        try:

            head = meal_info[0]["head"]

            for item in head:

                if "list_total_count" in item:

                    total_count = int(
                        item["list_total_count"]
                    )

                    break

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError
        ):

            total_count = None


        # ======================================
        # 현재 페이지 데이터
        # ======================================

        try:

            rows = meal_info[1]["row"]

        except (
            KeyError,
            IndexError,
            TypeError
        ):

            rows = []


        # ======================================
        # 데이터 저장
        # ======================================

        if rows:

            all_rows.extend(rows)


        # ======================================
        # 전체 데이터 수만큼 받았으면 종료
        # ======================================

        if total_count is not None:

            if len(all_rows) >= total_count:

                break


        # ======================================
        # 더 이상 데이터가 없으면 종료
        # ======================================

        if not rows:

            break


        page_index += 1


        # ======================================
        # 안전장치
        # ======================================

        if page_index > 100:

            break


    return all_rows, "OK"


# ==========================================
# 조회 버튼
# ==========================================

if st.button(
    "급식 데이터 조회",
    type="primary",
    use_container_width=True
):

    st.cache_data.clear()

    st.rerun()


# ==========================================
# 데이터 가져오기
# ==========================================

try:

    rows, result_message = get_all_meals(
        NEIS_API_KEY,
        start_ymd,
        end_ymd
    )

except requests.RequestException:

    st.error(
        "NEIS 서버에서 데이터를 가져오는 중 문제가 발생했습니다."
    )

    st.stop()

except Exception as e:

    st.error(
        f"데이터를 불러오는 중 문제가 발생했습니다: {e}"
    )

    st.stop()


# ==========================================
# API 오류
# ==========================================

if result_message != "OK":

    st.error(
        f"NEIS API 응답: {result_message}"
    )

    st.stop()


# ==========================================
# 데이터 없음
# ==========================================

if not rows:

    st.warning(
        f"{start_date.strftime('%Y년 %m월 %d일')}부터 "
        f"{end_date.strftime('%Y년 %m월 %d일')}까지 "
        "등록된 중식 급식 정보가 없습니다."
    )

    st.info(
        "조회 기간을 다른 날짜로 선택한 뒤 "
        "'급식 데이터 조회' 버튼을 눌러 보세요."
    )

    st.stop()


# ==========================================
# 데이터프레임 생성
# ==========================================

df = pd.DataFrame(rows)


# ==========================================
# 필요한 열 확인
# ==========================================

if (
    "MLSV_YMD" not in df.columns
    or "DDISH_NM" not in df.columns
):

    st.error(
        "NEIS 응답에서 날짜 또는 메뉴 데이터를 찾을 수 없습니다."
    )

    st.stop()


df = df[
    [
        "MLSV_YMD",
        "DDISH_NM"
    ]
].copy()


# ==========================================
# 날짜 변환
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
# 메뉴 분리
# ==========================================

menu_records = []


for _, row in df.iterrows():

    meal_date = row["날짜"]

    menu_text = str(
        row["DDISH_NM"]
    )


    # ======================================
    # <br/> 기준으로 나누기
    # ======================================

    menu_text = re.sub(
        r"<br\s*/?>",
        "\n",
        menu_text,
        flags=re.IGNORECASE
    )


    menu_list = menu_text.split(
        "\n"
    )


    # ======================================
    # 메뉴 하나씩 처리
    # ======================================

    for menu in menu_list:

        menu = menu.strip()


        if not menu:

            continue


        # ==================================
        # 괄호 속 알레르기 번호 제거
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
# 메뉴 데이터 없음
# ==========================================

if not menu_records:

    st.warning(
        "급식 데이터는 있지만 메뉴를 확인할 수 없습니다."
    )

    st.stop()


# ==========================================
# 메뉴 데이터프레임
# ==========================================

menu_df = pd.DataFrame(
    menu_records
)


# ==========================================
# 같은 날 같은 메뉴 중복 제거
# ==========================================

menu_df = menu_df.drop_duplicates(
    subset=[
        "날짜",
        "메뉴"
    ]
)


# ==========================================
# 집계한 날수
# ==========================================

counted_days = menu_df[
    "날짜"
].nunique()


# ==========================================
# 메뉴별 등장 일수
# ==========================================

menu_count = (
    menu_df
    .groupby("메뉴")["날짜"]
    .nunique()
    .reset_index(
        name="등장일수"
    )
)


# ==========================================
# 메뉴별 비율
# ==========================================

menu_count["비율"] = (
    menu_count["등장일수"]
    / counted_days
    * 100
)


# ==========================================
# 정렬
# ==========================================

menu_count = menu_count.sort_values(
    by=[
        "등장일수",
        "메뉴"
    ],
    ascending=[
        False,
        True
    ]
).reset_index(
    drop=True
)


# ==========================================
# 순위
# ==========================================

menu_count["순위"] = (
    menu_count.index + 1
)


# ==========================================
# 1위 메뉴
# ==========================================

first_menu = menu_count.iloc[0]

first_menu_name = first_menu[
    "메뉴"
]

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
        label="집계한 날수",
        value=f"{counted_days}일"
    )


with card2:

    st.metric(
        label="1위 메뉴",
        value=first_menu_name
    )


with card3:

    st.metric(
        label="1위 메뉴 비율",
        value=f"{first_menu_ratio:.1f}%"
    )


# ==========================================
# 순위 슬라이더
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
# 그래프 데이터
# ==========================================

display_df = menu_count.head(
    show_rank
).copy()


# ==========================================
# 1위가 맨 위에 오도록 정렬
# ==========================================

display_df = display_df.sort_values(
    by="등장일수",
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
        "비율": ":.1f"
    }
)


# ==========================================
# 막대에 값 표시
# ==========================================

fig.update_traces(
    texttemplate="%{text}일",
    textposition="outside"
)


# ==========================================
# 그래프 디자인
# ==========================================

fig.update_layout(
    height=max(
        400,
        show_rank * 55
    ),
    xaxis_title="등장한 일수",
    yaxis_title="메뉴",
    margin=dict(
        l=20,
        r=50,
        t=20,
        b=20
    )
)


# ==========================================
# 그래프 출력
# ==========================================

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==========================================
# 상세 표
# ==========================================

st.markdown("---")

st.markdown(
    "### 메뉴별 등장 일수와 비율"
)


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
