## Config flow tests

With Home Assistant, the integration's manifest requirements, `pytest` and `pytest-asyncio` installed, run this from the repository root.

```sh
python -m pytest -o addopts='' tests/test_config_flow.py
```

## Legacy tests

Run the following command from the repository root:

```


 sudo rm -rf **/__pycache__ && docker build -t test_ml .& docker run --rm -v ${PWD}:/app test_ml

 ```

 # Component TEst
 Uses `Dockerfile.component` to create home-assistant:dev environment image called:
 1. installs test dependencies
 2. runs `pytest-watch` using `pytest.ini` options

 `docker-compose up -d hass-test
 docker exec -it component-test /bin/bash



 ```

 run `ptw` inside container.
