# PoetgreSQL Guide

이 문서는 PostgreSQL를 생성하고, n8n에 연결하는 방법을 소개합니다. PostgreSQL는 기존의 SQLite와 다르게 환경 설정을 요구하며,`linux(ubuntu)`를 기준으로 `/var/lib/postgresql/{version}/main` 경로에 DB를 저장합니다. 또한 s Server-client 구조로 작동합니다.


## Database Schema

![Image](https://github.com/user-attachments/assets/01e4b216-90d6-4847-ab6b-20c571134162)

- `product_info`: ID, Amazon taxonomy(Main-Sub-Sub1-Sub2-Sub3)으로 구성되어 있습니다.
- `time_series_data`: ID, 시계열 데이터로 구성되어 있습니다.


## 🧐 How to Use??
### Step 1. Environment Setup : PostgreSQL을 활용하기 위해서는 초기 환경 설정이 필요합니다.
```bash
# Step 1. postgres 사용자로 전환
su - postgres
psql

# Step 2. Setup DB for PostgreSQL
CREATE DATABASE sales_data;
CREATE USER gorani WITH PASSWORD "password"; # 여러분이 원하는 비밀번호를 입력해주세요
GRANT ALL PRIVILEGES ON DATABASE sales_data TO gorani;
\c sales_data
GRANT ALL ON SCHEMA public TO gorani;

# Step 3. Exit PostgreSQL
\q
exit
```


### Step 2. CSV -> SQLite(DB) -> PostgreSQL : 전처리를 수행한 뒤에,CSV 파일을 DB로 변환하는 과정입니다.
```bash
# Pre-processing for amazon_categories.csv
poetry run python mapping.py

# CSV merge : train.csv & amazon_categories.csv
poetry run python csv_merge.py

# CSV -> DB : 위의 과정을 통해서 생성된, 전처리된 train.csv를 SQLite(.db)로 변환합니다.
poetry run python csv_to_db.py

# Db -> PostgreSQL : SQLite(.db)를 PostgreSQL로 변환합니다.
poetry run python db_to_postgre.py <Password>
```


### Step 3. n8n Docker를 위해서 Host 설정하기
n8n의 Docker에서 PosgreSQL에 접근하기 위해서는, `host.docker.internal`를 Host로 지정해야 합니다.

```bash
sudo systemctl status postgresql # Check if PostgreSQL is running

sudo nano /etc/postgresql/16/main/postgresql.conf
listen_addresses = '*' # 이 내용을 파일에 추가해주세요
```

![Image](https://github.com/user-attachments/assets/d1bfc714-e8c2-40cc-b958-9c3b6ee905a1)

### Step 4. n8n에 PostgreSQL 연결하기
n8n에서 PostgreSQL을 활용하기 위해서는 `PostgreSQL node`를 활용합니다. 아래의 이미지를 참고하여 설정해주세요.

![Image](https://github.com/user-attachments/assets/9a665b5f-150c-47d4-9a81-5dce3cd5a052)
