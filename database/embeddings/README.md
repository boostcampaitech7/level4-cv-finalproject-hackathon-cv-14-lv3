# Supabase Guide

이 문서는 Supabase에 저장된 임베딩 데이터를 활용하는 방법을 소개합니다. Supabase는 협업용 DB repository로 유용하며, vector embedding에 특화된 플랫폼 입니다.

## Database Schema

- `product_info`: 기존의 `product_info`에 임베딩 정보가 추가된 테이블입니다.
  ```sql
  CREATE TABLE product_info (
      id TEXT PRIMARY KEY,
      main TEXT,
      sub1 TEXT,
      sub2 TEXT,
      sub3 TEXT,
      embedding vector(384)
  );
  ```

![Image](https://github.com/user-attachments/assets/beabda25-0878-4693-b72f-c8c1b0768134)

## 🧐 How to Use?

Supabase 접속을 위한 환경변수를 설정합니다.
```bash
# .env 파일 생성
SUPABASE_URL=https://hjarbpzzhuqxeduvahyq.supabase.co
SUPABASE_KEY=<your-api-key>
```

### hierarchical_category_search.py : 카테고리 검색 실행
임베딩 처리된 데이터를 활용해 Input value에 대한 최적의 카테고리(main, sub1, sub2, sub3)를 찾습니다. SQLAlchemy를 활용하는 엔진에 사용될 코드로 수정할 필요가 있습니다.
```bash
# 카테고리 검색 실행
poetry run python hierarchical_category_search.py
```


## 📝 주요 파일 설명

- `supabase_uploader.py`: SQLite DB의 데이터를 Supabase로 업로드합니다.
- `hierarchical_category_search.py`: 텍스트 입력에 대한 최적의 카테고리 검색
- `.env`: Supabase 접속 정보 저장
