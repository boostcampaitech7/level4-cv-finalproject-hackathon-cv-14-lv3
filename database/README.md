## Database Structure

SQLite database는 2개의 table로 구성됩니다.
- `product_info` : 상품의 정보와 관련된 데이터가 있습니다.
- `time_series` : 시계열(날짜별 상품의 판매량) 데이터가 있습니다.

![Database Schema](https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3/tree/main/src/GORANI/src/db_mermaid.png)

### Relationships
- Each product in `product_info` can have multiple time series entries in `time_series_data`
- One-to-many relationship between `product_info` and `time_series_data`
- ID는 `PK/FK`에 해당하며, `1:n`의 관계성을 지닙니다.
