FROM python:3.7-buster
ENV PYTHONDONTWRITEBYTECODE 1

MAINTAINER Victor Ng <vng@mozilla.com>

RUN apt-get update && \
    apt-get install -y build-essential vim && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# First copy requirements.txt so we can take advantage of docker
# caching.
COPY requirements.txt /app/requirements.txt

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV PROC_DATE=""

#ENTRYPOINT /usr/bin/python -m taar_etl.taar_amodump --date=${PROC_DATE}


# bin/run supports web|web-dev|test options
CMD ["amodump"]
