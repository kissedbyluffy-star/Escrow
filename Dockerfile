FROM python:3.12-slim

RUN useradd -m appuser
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY escrow_bot /app/escrow_bot
COPY .env.example /app/.env.example

USER appuser
CMD ["python", "-m", "escrow_bot.app"]
