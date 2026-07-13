# syntax=docker/dockerfile:1

# Assemble the API's Lambda deployment zip inside the arm64 Lambda runtime image, so the
# dependencies are the exact native builds the function runs. Only the zip is exported
# (via the scratch stage); nothing is pushed as a container image.

FROM ghcr.io/astral-sh/uv:0.10.10 AS uv

FROM public.ecr.aws/lambda/python:3.12 AS builder

ENV UV_LINK_MODE=copy

# zip and find build the deployment archive; the minimal base image ships neither.
RUN dnf install -y zip findutils && dnf clean all

WORKDIR /build
COPY . .

# Install the locked api + cloud dependencies, then the project itself (installed, not
# copied, so its import metadata is present), into an isolated tree. Add the adapter
# startup script and zip it deterministically: normalized timestamps + sorted entries +
# no extra attributes make the archive byte-identical for identical input (a stable
# source_code_hash, so an unchanged build never redeploys). uv does not compile bytecode,
# so there is no __pycache__ to strip, which suits SnapStart anyway.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    uv export --frozen --no-dev --no-emit-project --extra api --extra cloud -o /tmp/requirements.txt \
    && uv pip install --python "$(command -v python3.12)" --target /asset -r /tmp/requirements.txt \
    && uv pip install --python "$(command -v python3.12)" --target /asset --no-deps . \
    && cp run.sh /asset/run.sh \
    && chmod +x /asset/run.sh \
    && cd /asset \
    && find . -type f -exec touch -t 198001010000.00 {} + \
    && find . -type f -printf '%P\n' | LC_ALL=C sort | zip -qX -9 /api.zip -@

FROM scratch AS export
COPY --from=builder /api.zip /api.zip
