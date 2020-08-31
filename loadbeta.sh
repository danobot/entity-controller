echo "Loading EC files from develop branch (beta version)..."
wget -O - -o /dev/null https://raw.githubusercontent.com/danobot/entity-controller/develop/custom_components/entity_controller/__init__.py > custom_components/entity_controller/__init__.py
wget -O - -o /dev/null https://raw.githubusercontent.com/danobot/entity-controller/develop/custom_components/entity_controller/const.py > custom_components/entity_controller/const.py
wget -O - -o /dev/null https://raw.githubusercontent.com/danobot/entity-controller/develop/custom_components/entity_controller/entity_services.py > custom_components/entity_controller/entity_services.py
wget -O - -o /dev/null https://raw.githubusercontent.com/danobot/entity-controller/develop/custom_components/entity_controller/manifest.json > custom_components/entity_controller/manifest.json
wget -O - -o /dev/null https://raw.githubusercontent.com/danobot/entity-controller/develop/custom_components/entity_controller/services.yaml > custom_components/entity_controller/services.yaml
echo "Done. Thanks for your contributions!"
