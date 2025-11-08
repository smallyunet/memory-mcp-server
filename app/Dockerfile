## Pinned Python base image for reproducibility (multi-arch official image)
FROM python:3.11.9-slim-bullseye

WORKDIR /app
COPY . /app
RUN rm -f /app/main.py || true

# Install required Python packages (MCP SDK and database stack)
# Use pip's --upgrade to ensure resolution against pinned versions and hash integrity possible later.
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8000
CMD ["python", "-u", "mcp_server.py"]
