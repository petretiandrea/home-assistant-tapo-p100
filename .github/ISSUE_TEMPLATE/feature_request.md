---
name: New Device Support Request
about: Suggest a new device to support or new functionality related to an already supported tapo device
---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Device Info**
Please execute this python script. You can save it as `main.py` and run it by using `python main.py`.
Be sure to have the latest version of `plugp100` library, by installing it through `pip install plugp100`.

```python
import asyncio

from plugp100 import TapoApiClient, TapoApiClientConfig, LightEffect

async def main():
    # create generic tapo api
    config = TapoApiClientConfig("<ip>", "<email>", "<passwd>")
    sw = TapoApiClient.from_config(config)
    await sw.login()
    await sw.on()
    await sw.set_brightness(100)
    state = await sw.get_state()
    print(state.get_unmapped_state())

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(0.1))
loop.close()

if __name__ == "__main__":
    main()
```
