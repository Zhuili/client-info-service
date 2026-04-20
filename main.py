from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import uvicorn

import config
from collector import collect, get_primary_ip, get_primary_mac, get_all_interfaces

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_key(key: str = Security(api_key_header)):
    if config.API_KEY and key != config.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )

app = FastAPI(title="Client Info Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/info", dependencies=[Depends(verify_key)])
def full_info():
    return collect()

@app.get("/ip", dependencies=[Depends(verify_key)])
def ip_only():
    return {"ip": get_primary_ip()}

@app.get("/mac", dependencies=[Depends(verify_key)])
def mac_only():
    return {"mac": get_primary_mac()}

@app.get("/interfaces", dependencies=[Depends(verify_key)])
def interfaces():
    return {"interfaces": get_all_interfaces()}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        ssl_certfile=config.TLS_CERT,
        ssl_keyfile=config.TLS_KEY,
        log_level="info",
    )
