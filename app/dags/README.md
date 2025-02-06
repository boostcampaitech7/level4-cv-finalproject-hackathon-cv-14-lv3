### 환경변수 설정
실행을 위해서는 환경변수(.env) 파일이 Root directory에 필요합니다.

```
SUPABASE_URL=<supabase_url>
SUPABASE_KEY=<supabase_api_key>
UPSTAGE_API_KEY=<upstage_api_key>
UPSTAGE_OCR_URL=https://api.upstage.ai/v1/vision/ocr
BASE_URL=https://datalab.naver.com/shoppingInsight/sCategory.naver?cid=5000000
```

### Airflow 설정
```bash
# Airflow home 디렉토리 설정
export AIRFLOW_HOME=~/airflow
poetry run airflow db init
```

### Airflow 관리자 계정 생성
``` bash
poetry run airflow users create \
    --username admin \
    --firstname admin \
    --lastname admin \
    --role Admin \
    --email admin@example.com \
    --password admin
```

### DAG 파일 연결
```
mkdir -p ~/airflow/dags
cd /path/to/project/app/dags
ln -s "$(pwd)/naver_crawler.py" ~/airflow/dags/
ln -s "$(pwd)/main.py" ~/airflow/dags/
```

### 실행 방법
``` bash
# Airflow 웹서버 실행 (터미널 1):
poetry run airflow webserver -p 8080

# Airflow 스케줄러 실행 (터미널 2):
poetry run airflow scheduler
```
- 웹 인터페이스 접속: 브라우저에서 0.0.0.0:8080 접속
- admin/admin으로 로그인
- DAGs 탭에서 'naver_crawler' DAG 활성화
- "Trigger DAG" 버튼으로 수동 실행 테스트 가능

### 스케줄링
매주 월요일 자정(0시 0분)에 자동 실행
스케줄 변경은 naver_crawler.py의 schedule 파라미터에서 수정 가능
poetry run airflow db init
