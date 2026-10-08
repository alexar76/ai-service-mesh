FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY ai_service_mesh ./ai_service_mesh
RUN pip install --no-cache-dir ".[postgres]"
ENV MESH_HOST=0.0.0.0
ENV MESH_PORT=8090
ENV MESH_DATA_DIR=/data
# The service fetches URLs that operators register and stores what comes back; it has
# no reason to be root inside the container. /data is the compose volume mount point.
RUN useradd -u 10001 -m mesh && mkdir -p /data && chown -R mesh:mesh /data /app
USER 10001
EXPOSE 8090
CMD ["python", "-m", "ai_service_mesh.main"]
