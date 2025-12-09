from fastapi import FastAPI

app = FastAPI(
    title="DocFlow Core API",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
