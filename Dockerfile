FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Render Web Service uses PORT env var (default 10000)
EXPOSE 10000

# Run bot
CMD ["python", "-m", "src.bot"]
