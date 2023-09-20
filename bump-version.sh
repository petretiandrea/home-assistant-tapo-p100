#/bin/bash

if ! [[ $1 =~ ^[v] ]]; then
    echo "Only version with vX.X.X are allowed"
    exit -1
fi

GIT_TAG_VERSION=$1
INTEGRATION_VERSION=${GIT_TAG_VERSION:1}


echo "Bumping const.py and manifest.json to version: $INTEGRATION_VERSION"
sed -i -E "s/VERSION = \"[0-9]+(\.[0-9]+)*\"/VERSION = \"$INTEGRATION_VERSION\"/g" custom_components/tapo/const.py
sed -i -E "s/\"version\": \"[0-9]+(\.[0-9]+)*\"/\"version\": \"$INTEGRATION_VERSION\"/gm" custom_components/tapo/manifest.json

git add custom_components/tapo/const.py
git add custom_components/tapo/manifest.json
git commit -m "bump version to $INTEGRATION_VERSION"

echo "Bump to version: $GIT_TAG_VERSION"
