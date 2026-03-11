FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# HF Spaces requires port 7860
EXPOSE 7860

# Run bot
CMD ["python", "-m", "src.bot"]
