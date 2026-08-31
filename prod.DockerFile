FROM python:3.12-slim

# Install dependencies for app
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
 
WORKDIR /workspaces/legoscanner

# Copy requirements
COPY requirements.prod.txt .
RUN pip3 install --no-cache-dir -r requirements.prod.txt

EXPOSE 8501

CMD ["streamlit", "run", "/workspaces/legoscanner/src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]