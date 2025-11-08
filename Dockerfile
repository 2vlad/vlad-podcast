# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies: ffmpeg, git, gh CLI
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Configure git for automated commits
RUN git config --global user.email "bot@railway.app" && \
    git config --global user.name "Railway Bot" && \
    git config --global credential.helper store

# Expose port (Railway will set PORT env variable)
EXPOSE 8080

# Start gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT web:app --workers 2 --timeout 120
