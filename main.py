import streamlit as st
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# ==========================================
# 페이지 설정
# ==========================================

st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🌸",
    layout="wide"
)


# ==========================================
# 핑크 테마
# ==========================================

st.markdown("""
<style>

    /* 전체 배경 */
    .stApp {
        background-color: #fff5f8;
    }

    /* 메인 제목 */
    h1 {
        color: #e75480;
        font-weight: 800;
    }

    /* 소제목 */
    h2, h3 {
        color: #d94f78;
    }

    /* 일반 글씨 */
    p, label {
        color: #5c3a45;
    }

    /* 입력창 */
    .stTextInput input {
        background-color: #fffafb;
        border: 2px solid #f3a6bb;
        border-radius: 12px;
    }

    .stTextInput input:focus {
        border-color: #e75480;
        box-shadow: 0 0 0 2px rgba(231, 84, 128, 0.15);
    }

    /* 선택창 */
    div[data-baseweb="select"] > div {
        background-color: #fffafb;
        border: 2px solid #f3a6bb;
        border-radius: 12px;
    }

    /* 날짜 선택창 */
    .stDateInput input {
        background-color: #fffafb;
        border: 2px solid #f3a6bb;
        border-radius: 12px;
    }

    /* 안내 박스 */
    .stAlert {
        border-radius: 14px;
    }

    /* 성공 메시지 */
    div[data-testid="stNotification"] {
        border-radius: 14px;
    }

    /* 구분선 */
    hr {
        border-color: #f7c6d5;
    }

    /* 메뉴 카드 느낌 */
    div[data-testid="stMarkdownContainer"] {
        color: #5c3a45;
    }

    /* 버튼 */
    .stButton button {
        background-color: #e75480;
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 700;
    }

    .stButton button:hover {
        background-color: #d94f78;
        color: white;
    }

</style>
""", unsafe_allow_html=True)


# ==========================================
# 제목
# ==========================================

st.title("🌸 학교 급식 찾아보기")
st.write("💗 학교를 검색하고 원하는 날짜의 중식 메뉴를 확인해 보세요.")


# ==========================================
# NEIS API
# ==========================================

SCHOOL_API = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# ==========================================
# 한국 시간
# ==========================================

KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.now(KST).date()


# ==========================================
# 학교 이름 축약어 변환
# ==========================================

def expand_school_name(name):

    name = name.strip()

    # 여고 → 여자고등학교
    name = name.replace(
        "여고",
        "여자고등학교"
    )

    # 마지막 고 → 고등학교
    if (
        name.endswith("고")
        and not name.endswith("고등학교")
    ):
        name = (
            name[:-1]
            + "고등학교"
        )

    return name


# ==========================================
# 학교 정보 API
# ==========================================

@st.cache_data(ttl=600)
def search_school(keyword):

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

        return [], "NETWORK_ERROR"

    except ValueError:

        return [], "JSON_ERROR"


    if "schoolInfo" not in data:

        return [], "INFO-200"


    try:

        rows = data[
            "schoolInfo"
        ][1]["row"]

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        return [], "INFO-200"


    return rows, "OK"


# ==========================================
# 학교 찾기
# ==========================================

def find_schools(keyword):

    keyword = keyword.strip()

    if not keyword:

        return [], False


    # 1차 검색
    schools, status = search_school(
        keyword
    )

    if (
        status == "OK"
        and schools
    ):

        return schools, False


    # 2차 검색
    expanded_name = expand_school_name(
        keyword
    )

    if expanded_name != keyword:

        schools, status = search_school(
            expanded_name
        )

        if (
            status == "OK"
            and schools
        ):

            return schools, True


    return [], False


# ==========================================
# 급식 정보 API
# ==========================================

@st.cache_data(ttl=600)
def search_meal(
    office_code,
    school_code,
    date_string
):

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


    for row in rows:

        if (
            row.get("MLSV_YMD")
            == date_string
        ):

            return row, "OK"


    return None, "INFO-200"


# ==========================================
# 학교 선택
# ==========================================

st.subheader("💗 1. 학교 선택")


school_keyword = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 수도여고"
)


if school_keyword.strip():

    schools, was_expanded = find_schools(
        school_keyword
    )


    # 줄임말을 풀어서 검색한 경우
    if was_expanded:

        expanded_name = expand_school_name(
            school_keyword
        )

        st.info(
            f"🌷 '{school_keyword}'로 찾지 못해 "
            f"'{expanded_name}'로 다시 검색했습니다."
        )


    # 학교를 찾지 못한 경우
    if not schools:

        st.warning(
            "🥲 입력한 학교를 찾지 못했습니다. "
            "학교 이름을 다시 확인해 주세요."
        )

        if "selected_school" in st.session_state:

            del st.session_state[
                "selected_school"
            ]


    else:

        # 중복 제거
        unique_schools = []
        seen = set()


        for school in schools:

            key = (
                school.get(
                    "ATPT_OFCDC_SC_CODE"
                ),
                school.get(
                    "SD_SCHUL_CODE"
                )
            )


            if key not in seen:

                seen.add(key)

                unique_schools.append(
                    school
                )


        schools = unique_schools


        # 학교 선택 목록
        school_options = {}


        for school in schools:

            school_name = school.get(
                "SCHUL_NM",
                ""
            )

            region = school.get(
                "LCTN_SC_NM",
                ""
            )


            label = (
                f"{region} · "
                f"{school_name}"
            )


            if label in school_options:

                label = (
                    f"{region} · "
                    f"{school_name} "
                    f"({school.get('SD_SCHUL_CODE', '')})"
                )


            school_options[
                label
            ] = school


        selected_label = st.selectbox(
            "학교를 선택하세요",
            list(
                school_options.keys()
            )
        )


        selected_school = school_options[
            selected_label
        ]


        st.session_state[
            "selected_school"
        ] = selected_school


# ==========================================
# 날짜 선택
# ==========================================

if "selected_school" in st.session_state:

    school = st.session_state[
        "selected_school"
    ]


    st.success(
        "🌸 선택한 학교: "
        f"{school.get('LCTN_SC_NM', '')} · "
        f"{school.get('SCHUL_NM', '')}"
    )


    st.subheader(
        "💗 2. 급식 날짜 선택"
    )


    selected_date = st.date_input(
        "날짜를 선택하세요",
        value=today_kst
    )


    date_string = selected_date.strftime(
        "%Y%m%d"
    )


    # ======================================
    # 급식 조회
    # ======================================

    meal, status = search_meal(
        office_code=school.get(
            "ATPT_OFCDC_SC_CODE"
        ),
        school_code=school.get(
            "SD_SCHUL_CODE"
        ),
        date_string=date_string
    )


    st.subheader(
        "🍚 3. 오늘의 중식"
    )


    # ======================================
    # 급식 있음
    # ======================================

    if (
        status == "OK"
        and meal
    ):

        menu = meal.get(
            "DDISH_NM",
            ""
        )

        calorie = meal.get(
            "CAL_INFO",
            ""
        )


        if not menu:

            st.info(
                "🌷 이날 등록된 중식 메뉴가 없습니다."
            )


        else:

            st.markdown(
                "### 🍓 메뉴"
            )


            # <br/> → 줄바꿈
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


            menu_items = [
                item.strip()
                for item in menu_text.split(
                    "\n"
                )
                if item.strip()
            ]


            for item in menu_items:

                st.write(
                    f"🌸 {item}"
                )


            # 알레르기 번호
            st.markdown(
                "### 🩷 알레르기 번호"
            )


            allergy_numbers = re.findall(
                r"\(([^()]*)\)",
                menu_text
            )


            if allergy_numbers:

                st.write(
                    " / ".join(
                        allergy_numbers
                    )
                )

            else:

                st.write(
                    "표시된 알레르기 번호가 없습니다."
                )


            # 칼로리
            st.markdown(
                "### 💕 칼로리"
            )


            if calorie:

                st.write(
                    calorie
                )

            else:

                st.write(
                    "칼로리 정보가 없습니다."
                )


    # ======================================
    # 급식 없음
    # ======================================

    elif status == "INFO-200":

        st.info(
            f"🌷 {selected_date.strftime('%Y년 %m월 %d일')}에는 "
            "등록된 중식 급식 정보가 없습니다."
        )


    # ======================================
    # 네트워크 오류
    # ======================================

    elif status == "NETWORK_ERROR":

        st.warning(
            "🥲 급식 정보를 가져오는 중 문제가 발생했습니다. "
            "잠시 후 다시 시도해 주세요."
        )


    # ======================================
    # 기타 오류
    # ======================================

    else:

        st.warning(
            "🥲 급식 정보를 확인할 수 없습니다. "
            "잠시 후 다시 시도해 주세요."
        )
