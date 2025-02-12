# AI 스마트 재고 관리 솔루션📦 "StockSense"

## 📖 Overview

- Duration : 2024.12.06 ~ 2025.02.12
- 네이버 부스트캠프 Level Upstage 기업 해커톤
- 트렌드 & 리콜 상품을 파악해 자동으로 최적의 재고를 관리하는 AI 재고 관리 솔루션


## 🧑‍💻 Contributors

|김태한|문채원|서동환|윤남규|이재훈|장지우
|:----:|:----:|:----:|:----:|:----:|:----:|
| [<img src="https://avatars.githubusercontent.com/u/84124094?v=4" alt="" style="width:100px;100px;">](https://github.com/taehan79-kim) <br/> | [<img src="https://github.com/user-attachments/assets/ea61c11c-c577-45bb-ae8e-64dffa192402" alt="" style="width:100px;100px;">](https://github.com/mooniswan) <br/> | [<img src="https://avatars.githubusercontent.com/u/87591965?v=4" alt="" style="width:100px;100px;">](https://github.com/Donghwan127) <br/> | [<img src="https://avatars.githubusercontent.com/u/152387005?v=4" alt="" style="width:100px;100px;">](https://github.com/Namgyu-Youn) <br/> | [<img src="https://github.com/user-attachments/assets/3ed91d99-0ad0-43ee-bb11-0aefc61a0a0e" alt="" style="width:100px;100px;">](https://github.com/syous154) <br/> | [<img src="https://github.com/user-attachments/assets/04f5faa7-05c4-4ecc-87f1-0befb53da70d" alt="" style="width:100px;100px;">](https://github.com/zangzoo) <br/> |

## 🔧 Tools

- 🧑‍💻 Programming : GitHub, VScode
- 🛠️ Development : n8n, FastAPI, React, Upstage API
- 👥 Communication : GitHub, Notion, Slack, Jira
- 🧱 Deployment : Docker

## 🚀 Setup & Installation

프로젝트를 실행하기 위한 기본 설정입니다:

- [Data](https://drive.google.com/file/d/16Dtf-Covz6-_RDhfMEyqVhFL-7yY5aeL/view?usp=drive_link)
- [Weight](https://drive.google.com/file/d/1k9muoQNIuIaRxXhtsa9-kvhXbv9L-elO/view?usp=drive_link)
- [WebShop](https://github.com/princeton-nlp/WebShop)

1. Repository Clone
```bash
git clone https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3.git
cd level4-cv-finalproject-hackathon-cv-14-lv3
```

2. How to Run
```bash
# Backend
cd backend
python main.py

# API Server
cd app
python api.py

# Frontend
cd frontend
npm install
npm start
```

<!--
더 자세한 설정 방법은 [Setup Guide](./docs/setup-guide.md)를 참고해주세요.
-->

## 📦 Folder Structure

```
├── app
│  ├── api.py
│  ├── dags
│  │  └── product_pipeline_dag.py # Airflow DAG pipeline
│  └── webshop_agent
│     ├── env_history.py # env in Web-shop
│     ├── generate_reflections.py # Reflection for faild trial
│     ├── run.py
│     └── webshop_trial.py # Web-shop Agent
├── backend
│  └── main.py  # FastAPI endpoints and routes
├── database
│  ├── format_converter  # DB migration : CSV->SQLite->PostgreSQL
│  └──  preprocessing  # DB preprocessing for column name,
└── frontend
   └── src
      ├── ChatPage.js # Chatbot UI
      ├── DashPage.js # Dashboard UI
      └── InventoryPage.js # Inventory UI
```


## Process

### Whole Process
![image](https://github.com/user-attachments/assets/b72a77d6-1195-4c5d-a7d3-4a597587a67f)
![Image](https://github.com/user-attachments/assets/f2c13f73-e9d1-41c0-87e9-f75062537456)

### Trend Product Search
![image](https://github.com/user-attachments/assets/4d595ddb-1c8e-4c20-aa49-abc10ccb021c)
![image](https://github.com/user-attachments/assets/69f8a292-badd-444d-b83f-57eb222c0e48)

### Recall Product Search
![image](https://github.com/user-attachments/assets/0cdf3dd9-e253-4696-ac47-ab6bffe5799e)

### UI
![대시보드_ppt](https://github.com/user-attachments/assets/4d97c0cd-e1aa-4ca1-968c-a0b392e14ab6)
![인벤토리](https://github.com/user-attachments/assets/953f676c-77a4-4d5a-80f2-503e12616636)
![챗봇_ppt](https://github.com/user-attachments/assets/cdbb3b4e-df05-47fc-bad4-d90fd76f3e6b)

## 📝 Wrap up Report
!다음 링크에서 저희조의 랩업리포트를 확인하실 수 있습니다: [Wrap up Report](https://github.com/boostcampaitech7/level4-cv-finalproject-hackathon-cv-14-lv3/blob/main/docs/wrapup_report.pdf)
