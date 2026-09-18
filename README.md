# NGC CPET

차세대스포츠과학지원센터 운동부하검사 피드백지 제작 웹앱입니다.

## 현재 구현 범위

- 선수 이름, 성별, 구분 등록
- 검사 기본 정보 입력
- BMI 직접 입력
- Excel `Data` 시트에서 `Time`, `VO2/kg`, `Heart Rate`, `Speed` 읽기
- `Speed` 변화 기준으로 Stage와 Rest 자동 구분
- 실제 측정 시간을 HR, VO2 그래프에 반영
- Stage별 HR, VO2 최소값, 최대값, 평균값 계산
- 혈중 젖산염 웹 직접 입력
- 미측정 젖산 Stage 자동 제외
- Rest는 LT 계산에서 제외
- 마지막 All-Out Stage는 LT 계산에 포함
- log10 공간 두 직선 분할회귀 기반 LT1 계산
- LT1 후구간 재분할 기반 LT2 계산
- 계산된 역치가 측정 부하 범위를 벗어나면 산출 불가 처리
- LT 수직선과 HR 곡선 교차 지점의 HR 표시
- 혈중 젖산염 전용 선그래프 생성
- A4 세로 2페이지 HTML 미리보기와 PDF 출력

## 로컬 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

macOS 또는 Linux에서는 가상환경 활성화 명령이 다릅니다.

## 배포

Streamlit Community Cloud에서 GitHub 저장소를 연결한 뒤 아래 항목으로 배포합니다.

- Repository: `Bogyeom99/ngc-cpet`
- Branch: `main`
- Main file path: `streamlit_app.py`

`packages.txt`는 배포 환경에서 한글 PDF와 그래프 글꼴을 지원하기 위한 시스템 패키지를 설치합니다.

## 다음 개발 범위

1. 기존 한컴 피드백지와 페이지 배치 세부 조정
2. 선수와 측정 기록 영구 저장
3. LT 결과 설명 문구 편집 기능
4. Speed와 Power 검사별 보고서 문구 자동 전환
5. 실제 검사 Excel 파일을 사용한 Stage 시간축 검증
