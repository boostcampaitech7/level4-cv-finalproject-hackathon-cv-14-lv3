import pandas as pd
from config import get_db_args
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

app = FastAPI(title="Sales Data API")
args = get_db_args()

# SQLAlchemy 엔진 생성
DATABASE_URL = f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.dbname}"
engine = create_engine(DATABASE_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {"message": "Welcome to Sales Data API", "endpoints": ["/products", "/sales/{product_id}"]}


@app.get("/products")
async def get_products():
    try:
        df = pd.read_sql("SELECT * FROM product_info", engine)
        return df.to_dict("records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sales/{product_id}")
async def get_sales(product_id: str):
    try:
        df = pd.read_sql("SELECT * FROM time_series_data WHERE id = %s", engine, params=(product_id,))
        if df.empty:
            raise HTTPException(status_code=404, detail="Product not found")
        return df.to_dict("records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
