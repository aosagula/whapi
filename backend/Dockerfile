FROM python:3.12-slim

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Instalar dependencias (capa cacheada separada del código fuente)
COPY pyproject.toml .
RUN mkdir -p app && touch app/__init__.py && \
    uv pip install --system --no-cache -e .

# Copiar código fuente
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
