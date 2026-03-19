FROM n8nio/n8n:latest

USER root
RUN apk add --no-cache python3 py3-pip
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

USER node
