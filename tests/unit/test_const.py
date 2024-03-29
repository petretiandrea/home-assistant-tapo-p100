from custom_components.tapo.const import PLATFORMS
from homeassistant.const import Platform


class TestHubPlatforms:
    def test_hub_platforms(self):
        expected_platforms = [
            Platform.SIREN,
            Platform.BINARY_SENSOR,
            Platform.SENSOR,
            Platform.SWITCH,
            Platform.CLIMATE,
            Platform.NUMBER,
        ]

        assert PLATFORMS == expected_platforms
