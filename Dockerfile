# Dockerfile - Containerize the Cyberbullying Detector Streamlit app
#
# Build:  docker build -t cyberbullying-app .
# Run:    docker run -p 8501:8501 cyberbullying-app
# Then open http://localhost:8501 in your browser.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by some Python packages (e.g. matplotlib, wordcloud)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]