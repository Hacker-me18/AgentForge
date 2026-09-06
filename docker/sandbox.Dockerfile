FROM python:3.11-slim

ENV MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# PIP_INDEX_URL can be overridden at build time, e.g.
# docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ...
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} \
    pandas~=2.2 \
    numpy~=2.0 \
    matplotlib~=3.9

RUN useradd -m sandbox
WORKDIR /work
USER sandbox

CMD ["python"]
