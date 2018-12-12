To run test suite, run the following command from root of repository:

```


 sudo rm -rf **/__pycache__ && docker build -t test_ml .& docker run --rm -v ${PWD}:/app test_ml

 ```