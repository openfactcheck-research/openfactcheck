FROM public.ecr.aws/lambda/python:3.12

COPY pyproject.toml VERSION LICENSE* README* ./
COPY src/ ./src/

RUN pip install --no-cache-dir ".[api,cloud]" mangum

CMD ["openfactcheck.api.lambda_handler.handler"]
