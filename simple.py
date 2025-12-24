import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"app": "Read Receipts", "status": "running"}

@app.get("/test")
def test():
    return {"message": "API is working!"}

if __name__ == "__main__":
    print("✓ Starting server...")
    print("✓ Open: http://localhost:8000")
    print("✓ Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8000)
