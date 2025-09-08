from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import logs, projects

app = FastAPI(title="LogCenter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router)
app.include_router(projects.router)

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
