FROM python:3.12-slim

# Update the package list, install sudo, create a non-root user, and grant password-less sudo permissions
RUN addgroup --gid $GID nonroot && \
    adduser --uid $UID --gid $GID --disabled-password --gecos "" nonroot && \
    echo 'nonroot ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# Set the non-root user as the default user
USER nonroot

# set working directory
WORKDIR /home/nonroot/app

# set environment variables
ENV APP_ENV=production
# ENV APP_ENV=development

# Install requirements
COPY src/pururu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY src/* ./


# Run the application
CMD ["python", "pururu/bot.py"]