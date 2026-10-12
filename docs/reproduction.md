# 로컬 재현과 검증

## 데이터 없이 보기

README와 assets의 집계 그림은 바로 볼 수 있다. `notebooks/01-analysis.ipynb`의 기본 셀은 공개된 집계 JSON만 읽는다. 실제 행 데이터나 인터넷 연결을 요구하지 않는다.

패키지 검사:

```powershell
python scripts/validate_repository.py
```

## 승인된 데이터로 재분석

실데이터·보조표는 저장소 밖에 둔 채 경로만 전달한다. 입력 3개는 CP949 거래 CSV, UTF-8 금리 CSV, UTF-8 추정 수수료 CSV다. 데이터명세는 [입력 설명](data-dictionary.md)에 있다. 

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts/run_analysis.py --transactions "<승인된 거래 CSV 경로>" --rates "<금리 CSV 경로>" --fees "<추정 수수료 CSV 경로>" --output "outputs/local-summary.json"
```

각 꺾쇠 자리만 실제 로컬 파일 경로로 바꾼다. 가상환경 생성·패키지 설치는 환경 변경/패키지 다운로드를 수행하지만 데이터 분석 스크립트는 외부 통신하지 않는다. 기존 output 파일이 있으면 덮어쓰지 않고 중단한다. 새 파일명을 지정해 비교한다.

`src/segmentation.py`는 읽은 표를 메모리에서 처리하고 `src/insights.py`가 집계 결과를 반환한다. `run_analysis.py`는 집계 JSON 한 개만 저장한다. 원자료를 삭제·이동·저장하지 않으며 관측 행을 내보내지 않는다. 실행 시 Python 캐시와 Matplotlib 글꼴 캐시가 로컬에 생길 수 있으며 Git 제외 대상이다.

그림은 검토된 집계 JSON으로만 만든다. 기존 이미지 폴더를 덮어쓰지 않도록 새 폴더를 지정한다.

```powershell
.venv\Scripts\python scripts/render_figures.py --summary outputs/local-summary.json --output-dir outputs/figures
```

Jupyter로 로컬 데이터까지 실행하려면 같은 가상환경을 커널로 선택하고 노트북의 주석 처리된 로컬 실행 예시를 채운다. Jupyter 확장/커널 도구는 별도로 필요하다. 기본 노트북에는 데이터 경로·원출력·실행 상태를 저장하지 않았다.

## 실제 확인한 범위

- 제공 CSV 347,299행·45열·36개월의 스키마·결측·구간 범주 확인.
- 원노트북의 전처리·지수·분류 핵심 셀을 실제 데이터로 재실행해 저장된 표본 수·Dunn p=1.0·디지털 p≈0.7878 재현.
- 오류 수정 후 정리한 전체 파이프라인 및 통계 검정 실행 완료. 분리 합계와 세그먼트 합계·수익 합계 대조.
- 원본과 수정본의 필터 전 데이터 동일성, 수정으로 추가 분리된 6행, 공통 관측의 수익 산식 값 보존 확인.
- 후속 후보 선별·경제성 계산·가중치 민감도 실행. 원본의 전체 무수정 Run All 또는 캠페인 실행을 뜻하지 않음.
- 원프로젝트 42개 파일과 데이터 폴더 4개 파일 해시 재확인. 원본 보존.

requirements.txt는 이번 실제 실행 환경의 직접 사용 분석 패키지 버전이다. 원래 팀 환경을 복원했다는 뜻은 아니다. Python 3.12.14에서 검증했다. 완전한 OS/하위 의존성 잠금 환경은 아니므로 다른 환경에서 재실행한 결과를 비교해야 한다.
