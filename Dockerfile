# --- STAGE 1: Base ---
FROM python:3.12-slim AS base

# Install common dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/legoscanner

# --- STAGE 2: Development ---
FROM base AS dev

# Install extra dev tools (git, curl)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Enable colorful terminal for root
ENV SHELL=/bin/bash
RUN echo 'export PS1="\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> /root/.bashrc && \
    echo 'alias ll="ls -la --color=auto"' >> /root/.bashrc    

# Install Dev requirements
COPY legoDisassemblyTracker/requirements.*.txt .
RUN pip3 install --no-cache-dir -r requirements.dev.txt

EXPOSE 8501 8888

# Launch JupyterLab, bind to all network interfaces, and allow running as root in container
ENTRYPOINT ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ContentsManager.allow_hidden=True", "--IdentityProvider.token=", "--ServerApp.password="]

# --- STAGE 3: Production ---
FROM base AS prod

# Install ONLY production requirements
COPY legoDisassemblyTracker/requirements.prod.txt .
RUN pip3 install --no-cache-dir -r requirements.prod.txt

# Copy app to image
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "/workspaces/legoscanner/legoDisassemblyTracker/Hello.py", "--server.port=8501", "--server.address=0.0.0.0"]