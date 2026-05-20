FROM python:3.12-slim

LABEL maintainer="matthewdeanmartin@gmail.com"
LABEL description="A Python tool to post calendar events to Mastodon"

WORKDIR /app

# Non-root user for runtime isolation
RUN useradd --create-home --shell /bin/bash appuser

# Install the package as root so the venv is system-wide, then drop to appuser
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir calendar2mastodon

# Drop privileges
USER appuser

# Default: show help.  Override CMD or pass arguments after the image name.
ENTRYPOINT ["calendar2mastodon"]
CMD ["--help"]
