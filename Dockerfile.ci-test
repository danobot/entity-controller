FROM python:3.6

RUN apt update
RUN apt install graphviz -y

COPY tests/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
ENV PYTHONPATH=/app
ADD . .
RUN chown root:root -R .


CMD [ "pytest", "./tests/test_lightingsm.py"]