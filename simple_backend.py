from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"app": "Read Receipts", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/test")
def test():
    return {
        "receipts": [
            {"merchant": "Lyft", "total": 22.74, "category": "transportation"},
            {"merchant": "Pizza", "total": 35.88, "category": "food"}
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Read Receipts backend...")
    print("🌐 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8000)
