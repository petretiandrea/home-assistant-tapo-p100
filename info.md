{% if prerelease %}

### NB!: This is a Beta version!

{% endif %}

# Home Assistant Tapo Integration

This is a custom integration to control Tapo devices from home assistant.

The core of the integration is provied by [plugp100](https://github.com/petretiandrea/plugp100) python library based on work of [@K4CZP3R](https://github.com/K4CZP3R/tapo-p100-python).

<!--- [![GitHub Release][releases-shield]][releases] -->
<!--- [![GitHub Activity][commits-shield]][commits] -->

[![License][license-shield]](LICENSE)

<!--- [![pre-commit][pre-commit-shield]][pre-commit] -->
<!--- [![Black][black-shield]][black] -->

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

## Features

- [x] pure async home assistant's method
- [x] support for tapo switch (`P100`, `P110`, `P105`)
- [x] support for tapo light bulb with or without color (`L530`, `L510`)
- [x] support for P110 energy monitoring
- [x] allow configuration from home assistant UI with config flow
- [x] allow configuration from `configuration.yaml`. supported domains are `switch`, `light`, `sensor`

## Installation

Recomended way:

1. Install from HACS, add this repository as custom repository
2. Search into HACS store the tapo integration and install
3. Full restart of home assistant is recomended

This video show installation steps:

[![Install Steps](http://img.youtube.com/vi/KSYldphgE5A/0.jpg)](https://youtu.be/KSYldphgE5A)

"Manual" way:

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `tapo`.
4. Download _all_ the files from the `custom_components/tapo/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "tapo"

## Configuration is done in the UI

1. Go to integrations menu
2. Search for `Tapo` integration
3. Insert host, username and password for control your tapo device
4. Wait for connection. It automatically recognize if the tapo device is switch or light
<!---->

## Configuration by configuration.yaml

Domain can be `switch`, `light` or `sensor`.

An example with switch:

```yaml
switch:
  platform: tapo
  host: ...
  username: ...
  password: ...
```

## Contributions are welcome!

Open a pull request, every contribution are welcome.

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/petretiandrea
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg
[commits-shield]: https://img.shields.io/github/commit-activity/y/petretiandrea/tapo.svg?style=for-the-badge
[commits]: https://github.com/petretiandrea/tapo/commits/main
[hacs]: https://github.com/petretiandrea/home-assistant-tapo-p100
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/petretiandrea/tapo.svg
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40petretiandrea-blue.svg
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/petretiandrea/tapo.svg?style=for-the-badge
[releases]: https://github.com/petretiandrea/home-assistant-tapo-p100/releases
[user_profile]: https://github.com/petretiandrea
