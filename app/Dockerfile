FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN rm -f /app/main.py || true

# Install required Python packages (MCP SDK and database stack)
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8000
CMD ["python", "-u", "mcp_server.py"]
