# FM_REA_HeadCoach (풋볼 매니저 실시간 전술 공략 & 유혈 지점 대시보드)

FM 실행 프로세스(`fm.exe`)의 실시간 데이터를 기반으로 **체력 감쇠에 따른 실효 능력치($\gamma(C)$)**, **6개 구역 공간 취약도($SVS$)**, **1:1 매치업 유혈 지점 확률($P_{\text{dribble}}, P_{\text{aerial}}, P_{\text{trap}}$)**, 그리고 **If-Then 전술 지시 가이드라인**을 실시간으로 산출하는 전술 대시보드입니다.

---

## 1. 즉시 실행 방법 (2가지 모드 지원)

### 방법 A: 브라우저 단독 즉시 실행 (설치 불필요)
- 프로젝트 폴더의 [`frontend/index.html`](file:///c:/GProjects/FM_REA_HeadCoach/frontend/index.html) 파일을 더블클릭하여 브라우저(Chrome/Edge)로 바로 엽니다.
- 상단 **3가지 전술 시나리오 프리셋** 버튼과 좌측 하단 **실시간 경기 변수 슬라이더**(상대 풀백 체력, 옐로카드 여부, 상대 수비 라인 높이, 상대 수비 폭)를 조작하면 0.01초 만에 6구역 히트맵, 1:1 돌파 기대 확률, 전술 지시 추천이 실시간으로 재계산됩니다.

### 방법 B: Python FastAPI + Pymem 실시간 메모리 리더 서버 실행
```powershell
cd c:\GProjects\FM_REA_HeadCoach\backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- 또는 루트 폴더의 [`run_dashboard.bat`](file:///c:/GProjects/FM_REA_HeadCoach/run_dashboard.bat)을 실행한 뒤 브라우저에서 `http://localhost:8000`에 접속합니다.
- Swagger API 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

---

## 2. 핵심 모듈 구성

- [`backend/app/models/match_state.py`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/models/match_state.py): 선수 23개 핵심 스탯, 실시간 체력/경고 상태, 팀 전술 슬라이더 및 분석 결과 데이터 스키마
- [`backend/app/engine/effective_stats.py`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/engine/effective_stats.py): 체력 $75\%$ 및 $55\%$ 기점 비선형 감쇠($\gamma(C)$) 및 옐로카드 페널티($-15\%$) 실효 스탯 계산기
- [`backend/app/engine/spatial_analyzer.py`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/engine/spatial_analyzer.py): 6개 피치 구역별 속도 격차($\Delta V$), 침투 격차($\Delta M$), 발목 회전/역동작 격차($\Delta A$) 및 전술 배율($M_{\text{tactic}}$) 기반 공간 취약도($SVS$) 산출기
- [`backend/app/engine/matchup_matrix.py`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/engine/matchup_matrix.py): 포지션별 1:1 매치업 시그모이드 확률 모델($P_{\text{dribble}}, P_{\text{aerial}}, P_{\text{press\_trap}}$) 및 유혈 지점(Bleed Point) 감지기
- [`backend/app/engine/rule_engine.py`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/engine/rule_engine.py): 히스테리시스(Hysteresis) 쿨다운이 적용된 If-Then 전술 지시(`R-01` ~ `R-06`) 자동 생성 규칙 엔진
- [`backend/app/memory/reader.py`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/memory/reader.py) & [`offsets.json`](file:///c:/GProjects/FM_REA_HeadCoach/backend/app/memory/offsets.json): `Pymem` 기반 `fm.exe` 프로세스 어태치 및 다중 포인터 체인 리졸버

