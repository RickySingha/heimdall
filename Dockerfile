# Stage 1: build; get required libraries
From python:3.12-slim AS builder

Workdir /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# stage 2: Run it
From python:3.12-slim

RUN useradd --create-home appuser
WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY app.py database.py ./

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
