import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        "app.main:app",   # change if your app path is different
        host="0.0.0.0",
        port=port,
    )
