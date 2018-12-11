FROM python:3.6

COPY tests/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
ENV PYTHONPATH=/app
# ADD . .
CMD [ "pytest" ]