FROM python:3.7-buster
ENV PYTHONDONTWRITEBYTECODE 1

MAINTAINER Victor Ng <vng@mozilla.com>

RUN apt-get update && \
    apt-get install -y build-essential vim && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# First copy requirements.txt so we can take advantage of docker
# caching.
COPY requirements.txt /app/requirements.txt

COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Running the TAAR job requires setting up AWS S3 credentials as well
# as a rundate for the job itself.

ENV PYTHONUNBUFFERED=1 \
    # AWS_ACCESS_KEY_ID= \
    # AWS_SECRET_ACCESS_KEY= \
    # AWS_DEFAULT_REGION= \
    # PROC_DATE= \

ENTRYPOINT ["/usr/local/bin/python"]
