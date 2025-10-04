FROM python:3.12-slim

# Create a non-root user and add sudo permision
RUN adduser --no-create-home nonroot
RUN usermod -aG sudo nonroot

# Update the package list and clenaup after the install
RUN apt update \
    && apt upgrade -y \
    && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove --purge  -y \
    && rm -rf /var/lib/apt/lists/*

# set working directory and ensure nonroot owns it
WORKDIR /home/nonroot/app
RUN chown -R nonroot:nonroot /home/nonroot

# set environment variables
ENV PURURU_APP_ENV=production

# Copy project files and install dependencies
COPY --chown=nonroot:nonroot . .

# Set the non-root user as the default user
USER nonroot

# Add user's local bin to PATH for installed scripts
ENV PATH="/home/nonroot/.local/bin:${PATH}"

# Install the package to user directory
RUN pip install --no-cache-dir --user .

# Run the application using the entry point
CMD ["pururu"]