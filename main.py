import streamlit as st
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# ---------------------------------------
# 기본 설정
# ---------------------------------------
st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍚",
    layout="wide"
)

st.title("학교 급식 찾아보기")
st.write("학교를 검색하고 원하는 날짜의 중식 메뉴를 확인해 보세요.")


SCHOOL_API = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# ---------------------------------------
# 한국 시간 기준 오늘 날짜
# ---------------------------------------
KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.now(KST).date()


# ---------------------------------------
# 학교 이름 축약어 보정
# ---------------------------------------
def expand_school_name(name):
    """
    학교 이름을 검색했는데 결과가 없을 때
    여고 → 여자고등학교
    고 → 고등학교
    로 바꿔서 다시 검색한다.
    """

    expanded = name.strip()

    # '여고'가 들어 있으면 '여자고등학교'로 변경
    expanded = expanded.replace("여고", "여자고등학교")

    # 마지막 글자가 '고'인 경우
    # 이미 '여자고등학교'로 바뀐 경우에는 건드리지 않는다.
    if expanded.endswith("고") and not expanded.endswith("고등학교"):
        expanded = expanded[:-1] + "고등학교"

    return expanded


# ---------------------------------------
# 학교 정보 API
# ---------------------------------------
@st.cache_data(ttl=600)
def search_school(keyword):
    """학교 이름으로 NEIS 학교정보를 검색한다."""

    params = {
        "Type": "json",
        "SCHUL_NM": keyword
    }

    try:
        response = requests.get(
            SCHOOL_API,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

    except requests.RequestException:
        return None, "NETWORK_ERROR"

    except ValueError:
        return None, "JSON_ERROR"

    # 데이터가 없는 경우
    if "schoolInfo" not in data:
        return [], "INFO-200"

    try:
        rows = data["schoolInfo"][1]["row"]
    except (KeyError, IndexError, TypeError):
        return [], "INFO-200"

    return rows, "OK"


# ---------------------------------------
# 학교 검색
# ---------------------------------------
def find_schools(keyword):
    keyword = keyword.strip()

    if not keyword:
        return [], False

    # 먼저 사용자가 입력한 그대로 검색
    schools, status = search_school(keyword)

    if status == "OK" and schools:
        return schools, False

    # 검색 결과가 없으면 축약어를 풀어서 다시 검색
    expanded = expand_school_name(keyword)

    # 변환 결과가 실제로 달라진 경우에만 다시 검색
    if expanded != keyword:
        schools, status = search_school(expanded)

        if status == "OK" and schools:
            return schools, True

    return [], False


# ---------------------------------------
# 급식 정보 API
# ---------------------------------------
@st.cache_data(ttl=600)
def get_meal(school_code, office_code, date_string):
    """
    선택한 학교의 특정 날짜 중식을 가져온다.
    """

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_string,
        "MLSV_TO_YMD": date_string,
        "pSize": "1000",
        "pIndex": "1"
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

    # 급식 데이터가 없는 경우
    if "mealServiceDietInfo" not in data:
        return None, "INFO-200"

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError, TypeError):
        return None, "INFO-200"

    if not rows:
        return None, "INFO-200"

    return rows[0], "OK"


# ---------------------------------------
# 학교 검색 입력
# ---------------------------------------
st.subheader("1. 학교 선택")

school_keyword = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 수도여고, 서울고등학교"
)


# ---------------------------------------
# 학교 검색 결과
# ---------------------------------------
if school_keyword.strip():

    schools, was_expanded = find_schools(school_keyword)

    if was_expanded:
        expanded_name = expand_school_name(school_keyword)

        st.info(
            f"'{school_keyword}'로 검색한 결과가 없어 "
            f"'{expanded_name}'로 다시 검색했습니다."
        )

    if not schools:
        st.warning(
            "입력한 학교를 찾지 못했습니다. "
            "학교 이름을 다시 확인해 주세요."
        )

        # 학교 선택 정보 초기화
        if "selected_school" in st.session_state:
            del st.session_state["selected_school"]

    else:
        # 같은 학교가 중복으로 나
