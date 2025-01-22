# PoetgreSQL Guide

이 문서는 PostgreSQL를 생성하고, n8n에 연결하는 방법을 소개합니다. PostgreSQL는 기존의 SQLite와 다르게 환경 설정을 요구하며,`linux(ubuntu)`를 기준으로 `/var/lib/postgresql/{version}/main` 경로에 DB를 저장합니다.

## 🧐 How to Use??
### Step 1. Environment Setup : PostgreSQL을 활용하기 위해서는 초기 환경 설정이 필요합니다.
```bash
# Step 1. postgres 사용자로 전환
su - postgres
psql

# Step 2. Setup DB in PostgreSQL
CREATE DATABASE sales_data;
CREATE USER gorani WITH PASSWORD "password"; # 여러분이 원하는 비밀번호를 입력해주세요
GRANT ALL PRIVILEGES ON DATABASE sales_data TO gorani;
\c sales_data
GRANT ALL ON SCHEMA public TO gorani;

# Step 3. Exit PostgreSQL
\q
exit
```


### Step 2. CSV -> PostgreSQL : 데이터 변환 및 저장
```bash
poetry run python csv_to_db.py <password>
```


### Step 3. n8n Docker를 위해서 Host 설정하기
n8n의 Docker에서 PosgreSQL에 접근하기 위해서는, `host.docker.internal`를 Host로 지정해야 합니다.

```bash
sudo systemctl status postgresql # Check if PostgreSQL is running

sudo nano /etc/postgresql/16/main/postgresql.conf
listen_addresses = '*' # 이 내용을 파일에 추가해주세요
```
![PostgreSQL result](https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3/tree/main/src/postgre_result.png)


### Step 4. n8n에 PostgreSQL 연결하기
n8n에서 PostgreSQL을 활용하기 위해서는 `PostgreSQL node`를 활용합니다. 아래의 이미지를 참고하여 설정해주세요.

![n8n_postgre](https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3/tree/main/src/postgre_result.png)


## 데이터베이스 구조

![Database Schema](https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3/tree/main/src/db_mermaid.png)

- `product_info`: 제품 기본 정보 (ID, 제품명, 카테고리 등)
- `time_series_data`: 시계열 데이터
