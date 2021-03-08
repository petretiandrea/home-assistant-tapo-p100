# tapo

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

**TO BE REMOVED: If you need help, as a developer, to use this custom component tempalte,
please look at the [User Guide in the Cookiecutter documentation](https://cookiecutter-homeassistant-custom-component.readthedocs.io/en/stable/quickstart.html)**

**This component will set up the following platforms.**

| Platform        | Description                                                               |
| --------------- | ------------------------------------------------------------------------- |
| `binary_sensor` | Show something `True` or `False`.                                         |
| `sensor`        | Show info from tapo API. |
| `switch`        | Switch something `True` or `False`.                                       |

![example][exampleimg]

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `tapo`.
4. Download _all_ the files from the `custom_components/tapo/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "tapo"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/tapo/translations/en.json
custom_components/tapo/translations/fr.json
custom_components/tapo/translations/nb.json
custom_components/tapo/translations/sensor.en.json
custom_components/tapo/translations/sensor.fr.json
custom_components/tapo/translations/sensor.nb.json
custom_components/tapo/translations/sensor.nb.json
custom_components/tapo/__init__.py
custom_components/tapo/api.py
custom_components/tapo/binary_sensor.py
custom_components/tapo/config_flow.py
custom_components/tapo/const.py
custom_components/tapo/manifest.json
custom_components/tapo/sensor.py
custom_components/tapo/switch.py
```

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/petretiandrea
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/petretiandrea/tapo.svg?style=for-the-badge
[commits]: https://github.com/petretiandrea/tapo/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/petretiandrea/tapo.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40petretiandrea-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/petretiandrea/tapo.svg?style=for-the-badge
[releases]: https://github.com/petretiandrea/tapo/releases
[user_profile]: https://github.com/petretiandrea
