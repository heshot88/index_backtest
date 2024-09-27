# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
import os
import subprocess
from dotenv import load_dotenv
import math
from datetime import datetime
import io
import site
import krx_tester.krx_backtester as kbt

st.set_page_config(layout="wide")

if st.secrets.load_if_toml_exists():
    github_token = st.secrets["github"]["token"]

    # Streamlit Secrets에서 연결 정보 가져오기
    db_user = st.secrets["postgres"]["user"]
    db_password = st.secrets["postgres"]["password"]
    db_host = st.secrets["postgres"]["host"]
    db_port = st.secrets["postgres"]["port"]
    db_name = st.secrets["postgres"]["dbname"]
else:
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")

    db_host = os.getenv('POSTGRESQL_HOST')
    db_port = os.getenv('POSTGRESQL_PORT')
    db_user = os.getenv('POSTGRESQL_USER')
    db_password = os.getenv('POSTGRESQL_PASSWORD')
    db_name = os.getenv('POSTGRESQL_DB')

#
# @st.cache_resource
# def install_package(url):
#     # subprocess.run([sys.executable, "-m", "pip", "install", url])
#     subprocess.run(["pip", "install", package_url], check=True)
#
#     # 설치된 패키지 경로 확인
#     result = subprocess.run(["pip", "show", "krx_backtester"], capture_output=True, text=True)
#     if result.returncode == 0:
#         print("krx_backtester 패키지가 설치된 경로:")
#         print(result.stdout)
#     else:
#         print("krx_backtester 패키지가 설치되지 않았습니다.")
#
#
# package_url = f"git+https://{github_token}@github.com/heshot88/krx_backtester.git#egg=krx_backtester"
# install_package(package_url)
# #
# # # 패키지 설치
# # os.system(f"pip install {package_url}") \
#

if 'conn' not in st.session_state:
    # Initialize connection.
    # st.session_state.conn = st.connection("postgresql", type="sql")

    # engine = create_engine(f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

    # 연결 확인
    try:
        st.session_state.conn = kbt.connect_db(db_host=db_host, db_port=db_port, db_user=db_user,
                                               db_password=db_password, db_name=db_name)
    except Exception as e:
        st.write("데이터베이스 연결 실패")
        print("데이터베이스 연결 실패:", str(e))

if 'show_table' not in st.session_state:
    st.session_state.show_table = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1


# 숫자만 입력되도록 필터링하는 함수
def only_numbers(value):
    # 입력된 값이 숫자인지 확인 (마이너스, 소수점 포함 가능)
    if value.replace('.', '', 1).replace('-', '', 1).isdigit() or value == '':
        return value
    else:
        return st.session_state[f'{value}_old']  # 유효하지 않으면 이전 값 반환


# 텍스트 입력 필드에서 숫자만 입력되도록 유효성 검사
def custom_number_input(label, value=0):
    # 상태 초기화
    if f'{label}_old' not in st.session_state:
        st.session_state[f'{label}_old'] = str(value)

    # 입력 받기 (기본적으로 str 타입)
    number_str = st.text_input(label, value=str(st.session_state[f'{label}_old']), key=label)

    # 유효성 검사 및 업데이트
    filtered_value = only_numbers(number_str)
    st.session_state[f'{label}_old'] = filtered_value

    # 변환된 숫자 값 반환
    return filtered_value if filtered_value == '' else float(filtered_value)


# 스타일링 함수 정의
def style_dataframe(df):
    # 개별 셀에 스타일 적용 함수
    def format_cell(value):
        if isinstance(value, float):
            # 소수점 값일 경우 100을 곱하고 % 추가
            return f"{value * 100:.2f}%"
        elif isinstance(value, int):
            # 정수일 경우 3자리 콤마 추가
            return f"{value:,}"
        else:
            return value

    # 전체 DataFrame에 포맷 적용
    styled_df = df.style.format(format_cell)

    # 헤더 스타일 지정: 중앙 정렬
    styled_df = styled_df.set_table_styles(
        {
            '': [{'selector': 'th', 'props': [('text-align', 'center')]}]  # 헤더 중앙 정렬
        }
    )
    # 데이터 셀 중앙 정렬
    styled_df = styled_df.set_properties(**{'text-align': 'center'})

    return styled_df


# 전체 화면을 사용하는 컨테이너 생성
with st.container():
    # 선택 상자 생성 (3개)

    # 중간에 위치하도록 좌우에 빈 공간을 둠
    left_spacer, center, right_spacer = st.columns([2, 2, 2])

    with center:
        # 내부에 또다시 3개의 컬럼으로 분할
        with st.container():
            col1, col2, col3 = st.columns(3)

            with col1:
                index_name = st.selectbox("지수", ["KOSPI", "KOSDAQ", "NASDAQ"])
            with col2:
                days_options_display = {
                    "일봉": "D",
                    "주봉": "W",
                    "월봉": "M"
                }
                days_options_list = list(days_options_display.keys())
                selected_display = st.selectbox("단위", days_options_list)
                ohlc_type = days_options_display[selected_display]
            with col3:
                current_year_start = datetime(datetime.today().year, 1, 1)
                st_date = st.date_input("시작날짜", value=current_year_start)

                st_date_str = str(st_date)

        with st.container():
            col4, col5 = st.columns(2)
            with col4:
                money = custom_number_input("투자 금액", value=100000000)
            with col5:
                initial_ratio = custom_number_input("첫 투자비율(%)", value=20)

        with st.container():
            col1, col2 = st.columns(2)
            with col4:
                main_buy_ratio = custom_number_input("매수 비율(%)", value=20)
            with col5:
                main_sell_ratio = custom_number_input("매도 비율(%)", value=20)

        with st.container():
            col1, col2 = st.columns(2)
            with col4:
                sub_buy_ratio = custom_number_input("인버스 매수 비율(%)", value=20)
            with col5:
                sub_sell_ratio = custom_number_input("인버스 매도 비율(%)", value=20)

        with st.container():
            col1, col2 = st.columns(2)
            with col4:
                buy_fee_rate = custom_number_input("매수 수수료율(%)", value=0.015)
            with col5:
                sell_fee_rate = custom_number_input("매도 수수료율(%)", value=0.2)

        with st.container():
            col1, col2, col3 = st.columns([5, 3, 1])
            with col2:
                order_display = {
                    "오름차순": True,
                    "내림차순": False,
                }
                order_options_list = list(order_display.keys())
                order_selected = st.selectbox("정렬", order_options_list)
                order_asc = order_display[order_selected]

            with col3:  # 조회 버튼 생성
                search_button = st.button(" 🔍 조  회 ")
    # 간격 추가
    st.write("<br><br>", unsafe_allow_html=True)  # 조회 버튼과 테이블 사이의 간격 조정

    # 버튼 클릭 시 결과 테이블 출력
    # 버튼 클릭 시 결과 테이블 출력
    if search_button:
        st.session_state.current_page = 1
        if initial_ratio > 0:
            is_first = True
        else:
            is_first = False
        if st.session_state.conn:
            result_df_t = kbt.sangwoo_01(st.session_state.conn, index_name, st_date_str, money, ohlc_type,
                                         initial_ratio, main_buy_ratio, main_sell_ratio, sub_buy_ratio,sub_sell_ratio,
                                         buy_fee_rate, sell_fee_rate, is_first)
            result_df = result_df_t.reset_index(drop=True)
        else:
            result_df = pd.DataFrame()

        # 데이터프레임을 세션 상태에 저장
        st.session_state.result_df = result_df
        st.session_state.show_table = True

    # 세션 상태에 따라 테이블 표시
    if st.session_state.show_table and 'result_df' in st.session_state:
        result_df = st.session_state.result_df
        # 데이터프레임의 인덱스를 제거한 상태로 출력
        result_df = result_df.sort_values(by="일자", ascending=order_asc)
        # 페이징 추가
        rows_per_page = 100

        # 전체 페이지 수 계산
        total_pages = math.ceil(len(result_df) / rows_per_page)

        # 전체 데이터 다운로드 버튼
        towrite = io.BytesIO()
        # encoding 인자를 제거하고 to_excel 호출
        result_df.to_excel(towrite, index=False, sheet_name='Sheet1')
        towrite.seek(0)

        # 현재 날짜와 시간을 사용하여 파일 이름 생성
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{index_name}_result_data_{current_time}.xlsx"

        # 현재 페이지 번호 선택

        # 2개의 열 생성 (비율 설정 가능)
        col1, col2 = st.columns([10, 1])  # 왼쪽 열은 3배 넓고, 오른쪽 열은 1배 넓음

        # 왼쪽 열에 내용 배치
        with col1:
            st.write("")
        # 오른쪽 열에 페이지 번호 입력 배치
        with col2:
            st.download_button(
                label="📥 엑셀 다운로드",
                data=towrite,
                file_name=file_name,  # 파일 이름에 날짜와 시간 추가
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            current_page = st.number_input("페이지 번호", min_value=1, max_value=total_pages,
                                           value=st.session_state.current_page)
            # 현재 페이지 정보 출력
            st.write(f"페이지 {current_page}/{total_pages}")

        st.session_state.current_page = current_page

        # 현재 페이지에 해당하는 데이터 슬라이싱
        start_idx = (current_page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        paged_df = result_df.iloc[start_idx:end_idx]

        # 테이블을 화면 전체 너비로 출력 (use_container_width=True)
        st.dataframe(style_dataframe(paged_df), use_container_width=True, height=1024)

st.markdown("""
    <style>
    /* 테이블 헤더 스타일 */
    .stDataFrame [role="columnheader"] div {
        justify-content: center;  /* 중앙 정렬 */
        max-width: 100px;         /* 헤더 너비 제한 */
        white-space: nowrap;      /* 텍스트 줄 바꿈 방지 */
    }

    /* 테이블 데이터 셀 스타일 */
    .stDataFrame [role="cell"] div {
        justify-content: center;  /* 중앙 정렬 */
        max-width: 100px;         /* 셀 너비 제한 */
        white-space: nowrap;      /* 텍스트 줄 바꿈 방지 */
    }
 
    </style>
    """, unsafe_allow_html=True)
