import streamlit as st
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# ==========================================
# 페이지 설정
# ==========================================

st.set_page_config(
    page_title="우리 학교 달력별 급식",
    page_icon="🍚",
    layout="wide"
)


# ==========================================
# 제목
# ==========================================

st.title("우리 학교 달력별 급식")
st.write("송탄고등학교의 날짜별 중식 메뉴를 확인해 보세요.")


# ==========================================
# 학교 정보
# ==========================================

SCHOOL_NAME = "송탄고등학교"

OFFICE_CODE = "J10"
SCHOOL_CODE = "7530480"

MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# ==========================================
# 한국 시간 기준 오늘 날짜
# ==========================================

KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.now(KST).date()


# ==========================================
# 급식 API
# ==========================================

@st.cache_data(ttl=600)
def get_meal(date_string):

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_string,
        "MLSV_TO_YMD": date_string
    }

    try:

        response = requests.get(
            MEAL_API,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException:

        return None, "NETWORK_ERROR"

    except ValueError:

        return None, "JSON_ERROR"


    # 급식 정보가 없는 경우
    if "mealServiceDietInfo" not in data:
        return None, "INFO-200"


    try:

        rows = data[
            "mealServiceDietInfo"
        ][1]["row"]

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        return None, "INFO-200"


    if not rows:
        return None, "INFO-200"


    # 선택한 날짜의 급식 찾기
    for row in rows:

        if row.get("MLSV_YMD") == date_string:
            return row, "OK"


    return None, "INFO-200"


# ==========================================
# 날짜와 알레르기 스위치
# ==========================================

date_col, allergy_col = st.columns([1.5, 1])


with date_col:

    st.markdown("### 날짜")

    selected_date = st.date_input(
        "급식 날짜",
        value=today_kst,
        label_visibility="collapsed"
    )


with allergy_col:

    st.markdown("### 알레르기 정보")

    show_allergy = st.toggle(
        "알레르기 정보 보기",
        value=True
    )


# ==========================================
# 선택한 날짜 표시
# ==========================================

st.markdown(
    f"### {selected_date.strftime('%Y년 %m월 %d일')} 중식"
)


# ==========================================
# 급식 조회
# ==========================================

date_string = selected_date.strftime("%Y%m%d")

meal, status = get_meal(date_string)


# ==========================================
# 급식이 없는 경우
# ==========================================

if status == "INFO-200" or meal is None:

    st.info("급식이 없는 날입니다.")


# ==========================================
# 급식이 있는 경우
# ==========================================

elif status == "OK":

    menu = meal.get(
        "DDISH_NM",
        ""
    )

    calorie = meal.get(
        "CAL_INFO",
        ""
    )


    # ======================================
    # 메뉴 문자열 정리
    # ======================================

    menu_text = menu.replace(
        "<br/>",
        "\n"
    )

    menu_text = menu_text.replace(
        "<br>",
        "\n"
    )


    # HTML 태그 제거
    menu_text = re.sub(
        r"<[^>]+>",
        "",
        menu_text
    )


    # 메뉴별로 나누기
    menu_items = [
        item.strip()
        for item in menu_text.split("\n")
        if item.strip()
    ]


    # ======================================
    # 알레르기 정보 끄기
    # ======================================

    if not show_allergy:

        cleaned_items = []

        for item in menu_items:

            # 메뉴 마지막의 괄호 안 알레르기 번호 제거
            # 예:
            # 김치찌개(5.6.9) → 김치찌개
            item = re.sub(
                r"\s*\([^()]*\)\s*$",
                "",
                item
            ).strip()

            cleaned_items.append(item)

        menu_items = cleaned_items


    # ======================================
    # 메뉴 가짓수와 칼로리
    # ======================================

    count_col, calorie_col = st.columns(2)


    with count_col:

        st.metric(
            label="메뉴 가짓수",
            value=f"{len(menu_items)}가지"
        )


    with calorie_col:

        st.metric(
            label="칼로리",
            value=calorie if calorie else "정보 없음"
        )


    st.markdown("---")


    # ======================================
    # 메뉴 카드
    # ======================================

    st.markdown("### 오늘의 메뉴")


    if menu_items:

        # 한 줄에 3개의 메뉴 카드
        columns = st.columns(3)


        for index, item in enumerate(menu_items):

            with columns[index % 3]:

                st.container(
                    border=True
                )

                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"### 🍚 {item}"
                    )


    else:

        st.info(
            "등록된 메뉴가 없습니다."
        )


# ==========================================
# 네트워크 오류
# ==========================================

elif status == "NETWORK_ERROR":

    st.warning(
        "급식 정보를 가져오는 중 문제가 발생했습니다. "
        "잠시 후 다시 시도해 주세요."
    )


# ==========================================
# 기타 오류
# ==========================================

else:

    st.warning(
        "급식 정보를 확인할 수 없습니다. "
        "잠시 후 다시 시도해 주세요."
    )
