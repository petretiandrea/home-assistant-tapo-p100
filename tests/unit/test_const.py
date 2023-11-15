from custom_components.tapo.const import *


class TestHubPlatforms:

    def test_hub_platforms(self):
        expected_platforms = \
        {
            Platform.SIREN,
            Platform.BINARY_SENSOR,
            Platform.SENSOR,
            Platform.SWITCH,
            Platform.CLIMATE,
            Platform.NUMBER
        }

        assert HUB_PLATFORMS == expected_platforms
