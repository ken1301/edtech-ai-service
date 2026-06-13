Run these commands to set up the AI service package:
```bash
git clone https://github.com/trinhkhanh15/ai-service.git

cd ai-service

python -m venv .venv # python3 on Unix or MacOS
.venv\Scripts\activate # On Windows
source .venv/bin/activate # On Unix or MacOS

pip install -r requirements.txt

python -m uvicorn adapters.inbound.rest.main:app --reload
```
- Make sure you have Python 3.10 or higher installed. The AI service will be running at `http://localhost:8000`. You can test the endpoints using tools like Postman or curl.
- Make sure to use this docker-compose file (find in the root directory) to run the AI service with all its dependencies.