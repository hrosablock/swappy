FROM python:3.9-slim

WORKDIR /app

RUN apt update && apt install -y build-essential python3-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .  

RUN pip install --no-cache-dir -r requirements.txt  

COPY bot /app/bot  

CMD ["python", "-m", "bot"]
