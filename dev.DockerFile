FROM python:3.12-slim

# Install dependencies for app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Enable colorful terminal for root
ENV SHELL=/bin/bash
RUN echo 'export PS1="\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> /root/.bashrc && \
    echo 'alias ll="ls -la --color=auto"' >> /root/.bashrc
 
WORKDIR /workspaces/legoscanner

# Copy requirements
COPY requirements*.txt .
RUN pip3 install --no-cache-dir -r requirements.dev.txt

EXPOSE 8501 8888

# Launch JupyterLab, bind to all network interfaces, and allow running as root in container
ENTRYPOINT ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ContentsManager.allow_hidden=True"]