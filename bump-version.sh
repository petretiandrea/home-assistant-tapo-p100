#/bin/bash
GIT_TAG_VERSION=$1
INTEGRATION_VERSION=GIT_TAG_VERSION


echo "Bumping const.py and manifest.json to version: $INTEGRATION_VERSION"
sed -i -E "s/VERSION = \"[0-9]+(\.[0-9]+)*\"/VERSION = \"$INTEGRATION_VERSION\"/g" custom_components/tapo/const.py
sed -i -E "s/\"version\": \"[0-9]+(\.[0-9]+)*\"/\"version\": \"$INTEGRATION_VERSION\"/gm" custom_components/tapo/manifest.json

echo "Bump to version: $GIT_TAG_VERSION"
