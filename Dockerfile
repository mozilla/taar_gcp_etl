FROM continuumio/miniconda3
ENV PYTHONDONTWRITEBYTECODE 1

MAINTAINER Victor Ng <vng@mozilla.com>

# add a non-privileged user for installing and running
# the application
RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app 

RUN apt-get update && \
    apt-get install -y build-essential vim && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN make setup_conda

RUN . /opt/conda/etc/profile.d/conda.sh && \
    conda activate taar_gcp_etl && \
    python setup.py install

USER app

ENTRYPOINT ["/bin/bash", "/app/bin/run"]
