FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV FLASK_CONFIG=production
ENV FLASK_DEBUG=false
ENV RAG_ENABLED=false

EXPOSE 5003

CMD ["python", "run.py"]
