# Home Assistant Tapo Integration

This is a custom integration to control Tapo devices from home assistant.

The core of the integration is provied by [plugp100](https://github.com/petretiandrea/plugp100) python library based on work of [@K4CZP3R](https://github.com/K4CZP3R/tapo-p100-python).

<!-- [![GitHub Release][releases-shield]][releases] -->
<!--- [![GitHub Activity][commits-shield]][commits] -->

<!--- [![pre-commit][pre-commit-shield]][pre-commit] -->
<!--- [![Black][black-shield]][black] -->

[![Stable Release][stable_release]][stable_release]
[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![License][license-shield]](LICENSE)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

Please help me to complete the [new roadmap](https://github.com/petretiandrea/home-assistant-tapo-p100/discussions/655)

## Sponsors
### Gold Sponsors

<!-- gold --><!-- gold -->

### Silver Sponsors

<!-- silver --><a href="https://github.com/jmd-au"><img src="https://github.com/jmd-au.png" width="60px" alt="James Mac" /></a><!-- silver -->

## Warnings

### Tapo protocol

Tapo is updating its devices with a new firmware which use a new protocol called KLAP. This integration support it's but if you running older version your devices maybe cannot works. So please keep this integration up to date by using HACS!

### Local Integration

Although the integration works using LAN, the tapo device needs internet access to synchronize with tapo cloud, especially for credentials, a missing internet access could lead into "Invalida authentication error". Also a static IP must be set for device.

### Authentication

For some unknown reason email with capital letter thrown an "Invalid authentication" error. So before open an new issue check your email address on Tapo App Settings. If contains capital letter, the integration won't work. I've opened an issue that explain this [#122](https://github.com/petretiandrea/home-assistant-tapo-p100/issues/122), I will fix asap. As workaround you can create a new account using all lower-case in your email address.

## Features

### Discovery

The integration now supports native tapo discovery! To enable it you must add at least one tapo device or this line to your tapo configuration file

```yaml
tapo:
  discovery: true # you can omit "discovery" by default, with "tapo:" it will enable discovery automatically.
```

This will enable tapo device discovery. Not all tapo devices supports tapo discovery, so if you not find it, try adding manually.
Also tapo integration discovery filters out not supported devices!

<details>
  <summary>Screenshot</summary>
  
  ![Discovery](/docs/discovery-devices.png)

</details>

You can disable integration discovery by editing `configuration.yaml` in the following way:

```yaml
tapo:
  discovery: false
```

#### Device IP Tracking

By using DHCP home assistant discovery the feature of mac tracking is now disabled, cause HA can track it automatically now.
Please be sure to have DHCP discovery not disabled on your `configuration.yaml` (by default is active).

[BREAKING] Tracking mac address feature is now disabled cause not recommended by HA. The tracking is now performed by HA itself.

### Supported devices

- [x] pure async home assistant's method
- [x] support for tapo `H100` hub and siren
- [ ] support for tapo `H100` hub is currently Work In Progress!
- [x] support for `T31x` temperature and humidity sensor hub's device
- [x] support for `T100` motion sensor hub's device
- [x] support for `T110` smart door hub's device
- [x] support for `S220`, `S210` switch hub's device
- [x] partial support for `S200B` button hub's device (actually no events are reported to HA)
- [x] support for tapo powerstrip (`P300`). A special thanks go to @alxlk to support me with max one-time contribution which allows me to buy the device
- [x] support for tapo switch (`P100`, `P110`, `P105`, `P115`, `P125`, `P110M`)
- [x] support for tapo light bulb with or without color (`L530`, `L510`, `L520`, `L630`, `L610`, `L530B`, `L530E`)
- [x] support for tapo light strip with or without color (`L900`)
- [x] partial support for tapo light strip (`L920`, `L930` (including light effects)). Only RGB works not the addressable feature of strip.
- [x] support for energy monitoring (`P110`, `P115`, `P110M`)
- [x] support for tapo light switches with or without the dimmer (`S500`, `S500d`, `S505d`)
- [x] support for KE100 by @delatt
- [x] support for additional tapo sensors: `overheat` and `wifi_signal`
- [x] allow configuration from home assistant UI with config flow
- [x] allow configuration from `configuration.yaml`. supported domains are `switch`, `light`, `sensor`

### Additional features

- [x] manually change ip address. Now you can change the ip address of a tapo device wihtout removing and re-adding it.

# How to install

This integration is part of HACS store, so you don't need anymore to add this repository as a custom repository.
You can find it directly on HACS Store: search for `tapo` and you will find `Tapo Controller`. (**HACS >= 1.6.0 is required**)

This video show installation steps:

[![Install Steps](http://img.youtube.com/vi/KSYldphgE5A/0.jpg)](https://youtu.be/KSYldphgE5A)

# How to add a Tapo device (after installing the integration)

## Using UI

1. Be sure the integration is installed successfully
2. Go to integrations menu
3. Search for `Tapo` integration
4. Insert host (ip address), username and password for control your tapo device (the same used for tapo app).
   If you have a problem in this phase, like "invalid auth" error, please see [#122](https://github.com/petretiandrea/home-assistant-tapo-p100/issues/122), and if error persist write a comment in the same issue
5. Wait for connection. It automatically recognize if the tapo device is switch or light or something else :)
<!---->

## Configuration by configuration.yaml

[BREAKING]

The latest version of this integration remove configuration.yaml device configuration support. This
is due to follow home assistant best practices https://developers.home-assistant.io/docs/configuration_yaml_index/ and https://github.com/home-assistant/architecture/blob/master/adr/0010-integration-configuration.md#decision

## Beta versions

To access to beta version, you must install it as custom

1. Install from HACS, add this repository as custom repository
2. Search into HACS store the tapo integration and install
3. Full restart of home assistant is recommended

## Contributions are welcome!

Open a pull request, every contribution are welcome.

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/petretiandrea
[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png
[commits-shield]: https://img.shields.io/github/commit-activity/y/petretiandrea/tapo.svg?style=for-the-badge
[commits]: https://github.com/petretiandrea/tapo/commits/main
[hacs]: https://github.com/petretiandrea/home-assistant-tapo-p100
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/petretiandrea/home-assistant-tapo-p100.svg
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40petretiandrea-blue.svg
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/petretiandrea/tapo.svg?style=for-the-badge
[releases]: https://github.com/petretiandrea/home-assistant-tapo-p100/releases
[user_profile]: https://github.com/petretiandrea
[stable_release]: https://img.shields.io/github/v/release/petretiandrea/home-assistant-tapo-p100?label=stable&sort=semver
