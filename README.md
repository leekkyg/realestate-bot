# 여주굿뉴스 부동산 실거래가 자동화

국토교통부 실거래가 API를 사용하여 여주시 부동산 거래 정보를 자동으로 워드프레스에 발행합니다.

## 📋 기능

- 국토교통부 아파트 매매 실거래가 API 연동
- 여주시 법정동 코드: 41670
- 다크모드 UI + 접이식 카드 디자인
- 신규(NEW) 뱃지 자동 표시
- 평당가 자동 계산
- 터치/스크롤 구분 처리 (모바일 최적화)
- GitHub Actions로 주 2회 자동 실행

## 🚀 설정 방법

### 1. 국토교통부 실거래가 API 신청

1. [공공데이터포털](https://www.data.go.kr) 회원가입/로그인
2. **"국토교통부_아파트 매매 실거래가 자료"** 검색
3. **활용신청** 클릭
4. 활용목적 작성:
   ```
   지역신문(여주굿뉴스) 부동산 실거래가 정보 서비스 제공
   ```
5. 신청 후 **즉시~1시간 내 승인** (자동승인)

### 2. API 키 확인

마이페이지 → 데이터 활용 → 승인된 API 클릭 → **인증키(Encoding)** 복사

### 3. GitHub Secrets 설정

리포지토리 Settings → Secrets and variables → Actions:

| Secret 이름 | 설명 | 예시 |
|------------|------|------|
| `MOLIT_API_KEY` | 국토교통부 API 인증키 (Encoding) | `XXXXX...` |
| `WP_URL` | 워드프레스 사이트 URL | `https://yeojugoodnews.com` |
| `WP_USER` | 워드프레스 사용자명 | `admin` |
| `WP_APP_PASSWORD` | 워드프레스 앱 비밀번호 | `xxxx xxxx xxxx xxxx` |

## 📁 파일 구조

```
yeoju-realestate/
├── fetch_realestate.py           # 메인 스크립트
├── .github/
│   └── workflows/
│       └── realestate.yml        # GitHub Actions
└── README.md
```

## ⏰ 실행 스케줄

| 요일 | 시간 (KST) |
|-----|-----------|
| 월요일 | 09:00 |
| 목요일 | 09:00 |

※ 실거래 신고는 계약일로부터 30일 이내이므로 주 2회 업데이트가 적당

수동 실행: Actions 탭 → "여주 부동산 실거래가 자동 발행" → "Run workflow"

## 🧪 로컬 테스트

```bash
# 환경변수 설정
export MOLIT_API_KEY="your_api_key"
export WP_URL="https://yeojugoodnews.com"
export WP_USER="your_username"
export WP_APP_PASSWORD="your_app_password"

# 실행
python fetch_realestate.py
```

워드프레스 정보 없이 실행하면 HTML 파일로 저장됩니다.

## 📊 제공 정보

### 통계
- 월별 거래 건수
- 평균 거래가
- 최근 7일 거래
- 최고가 거래
- 최다 거래 단지

### 거래 상세
- 아파트명, 주소
- 거래금액, 평당가
- 전용면적, 층
- 건축년도
- 계약일, 거래유형

## 🔧 커스터마이징

### 다른 지역으로 변경

```python
# fetch_realestate.py에서 법정동 코드 변경
YEOJU_CODE = '41670'  # 여주시

# 다른 지역 코드 예시:
# 11110 - 서울 종로구
# 41135 - 경기 성남시 분당구
# 41590 - 경기 이천시
```

### 발행 빈도 변경

`.github/workflows/realestate.yml`에서 cron 표현식 수정

## 📝 API 참고

- [공공데이터포털 - 아파트 매매 실거래가](https://www.data.go.kr/data/15126469/openapi.do)
- 요청 파라미터:
  - `LAWD_CD`: 법정동코드 앞 5자리
  - `DEAL_YMD`: 계약년월 (YYYYMM)
- 일일 호출 제한: 1,000건 (개발) / 10,000건 (운영)

## ⚠️ 주의사항

- API 키는 2년마다 갱신 필요
- 실거래 신고 후 자료 반영까지 시차 있음 (통상 1~2주)
- 월초에는 해당 월 데이터가 적을 수 있음 → 자동으로 전월 데이터 포함
- 개인정보 보호로 동 정보는 등기 완료 후 공개
