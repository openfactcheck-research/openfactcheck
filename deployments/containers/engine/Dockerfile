FROM public.ecr.aws/lambda/python:3.12

COPY pyproject.toml VERSION LICENSE* README* ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

CMD ["openfactcheck.engine.lambda_handler.handler"]
