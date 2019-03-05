# Notice:
# When updating this file, please also update virtualization/Docker/Dockerfile.dev
# This way, the development image and the production image are kept in sync.

FROM homeassistant/home-assistant:dev


# RUN script/setup

COPY requirements_test_all.txt requirements_test_all.txt
RUN pip3 install -r requirements_test_all.txt

COPY requirements_test.txt requirements_test.txt
RUN pip3 install -r requirements_test.txt

# RUN apt install -y apt-get install python3-pip python3-dev python3-venv autoconf libssl-dev libxml2-dev libxslt1-dev libjpeg-dev libffi-dev libudev-dev zlib1g-dev
ADD ./custom_components/entity_controller/__init__.py /usr/src/app/homeassistant/components/entity_controller/__init__.py
ADD ./tests/test_lightingsm.py /usr/src/app/tests/components/test_lightingsm.py
ADD ./pytest.ini /usr/src/app/pytest.ini

# RUN chown root:root -R ./tests/components/test_lightingsm.py ./components/lightingsm.py
#CMD [ "ptw","--","-sv" ]
#RUN apt update
#RUN apt install graphviz -y
CMD ["/bin/bash"]
