from fastapi import FastAPI

app = FastAPI(title='LogCenter API')

@app.get('/health')
def health():
    return {'status': 'ok'}
