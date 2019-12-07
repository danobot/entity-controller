sudo rm -rf **/__pycache__ && docker build -t test_ml . && docker run --rm -v ${PWD}:/app test_ml


sudo docker build -t test_ml .

