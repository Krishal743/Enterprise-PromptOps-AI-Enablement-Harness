FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY ops_ai ./ops_ai
COPY data ./data
COPY prompts ./prompts
COPY playground.py ./playground.py
RUN python -m pip install --no-cache-dir -e '.[playground]'

ENV OPS_LLM_PROVIDER=mock
CMD ["uvicorn", "ops_ai.api:app", "--host", "0.0.0.0", "--port", "8000"]
