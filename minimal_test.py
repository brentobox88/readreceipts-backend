# minimal_test.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "working"}

@app.get("/health")
async def health():
    return {"status": "healthy", "test": "true"}

if __name__ == "__main__":
    print("🚀 Starting minimal test server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
