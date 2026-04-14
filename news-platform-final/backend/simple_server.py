from fastapi import FastAPI

app = FastAPI(title="News Platform - Minimal Backend")

@app.get("/")
async def root():
    return {"status": "running", "message": "News Platform Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005, reload=True)
