"""
Root entry point for Application Layer Visualizer.
Enables zero-config deployment on Railpack, Railway, Render, and cloud PaaS.
"""
import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
