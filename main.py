import logging
import uvicorn
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8081,
        reload=False, 
    )