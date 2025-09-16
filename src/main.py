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

