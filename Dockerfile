# Rain — minimal image. Set ANTHROPIC_API_KEY or OPENAI_API_KEY at runtime.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
EXPOSE 8765
CMD ["python", "-m", "rain", "--web", "--port", "8765"]
