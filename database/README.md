# PoetgreSQL Guide

이 문서는 PostgreSQL을 사용법에 대해서 소개합니다. PostgreSQL는 기존의 SQLite와 다르게 비밀번호를 요구하며,linux를 기준으로 아래의 경로에 저장됩니다.

```
/var/lib/postgresql/{version}/main
```

## How to Use??
### 1. 데이터베이스 설정

```bash
# postgres 사용자로 전환
su - postgres
psql

# PostgreSQL에서 실행
CREATE DATABASE sales_data;
CREATE USER sales_user WITH PASSWORD 'your_password'; # 여러분이 원하는 비밀번호를 입력해주세요
GRANT ALL PRIVILEGES ON DATABASE sales_data TO sales_user;
\c sales_data
GRANT ALL ON SCHEMA public TO sales_user;
```

### 2. 데이터 변환 및 저장
```bash
poetry run python csv_to_db.py
```

### 3. Local hosting with
```bash
# SQL 파일로 추출
pg_dump -U sales_user sales_data > sales_data.sql

# 또는 CSV 파일로 추출
poetry run python export_to_db.py
```

## 데이터베이스 구조

![Database Schema](https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3/tree/main/src/db_mermaid.png)

- `product_info`: 제품 기본 정보 (ID, 제품명, 카테고리 등)
- `time_series_data`: 시계열 데이터

## Troubleshooting

권한 문제 발생 시:
```sql
ALTER SCHEMA public OWNER TO sales_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sales_user;
```
