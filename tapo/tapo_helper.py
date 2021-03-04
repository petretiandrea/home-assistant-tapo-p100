import base64
import logging

from typing import *
from plugp100 import P100
from plugp100.models.exceptions.ResponseErrorCodeNotZero import ResponseErrorCodeNotZero

_LOGGER = logging.getLogger(__name__)

SUPPORTED_DEVICE_AS_SWITCH = ["p100"]

# TODO: improvements
# - check if there is need to handshake and login everytime. This is related to token expire time
# - simplify (or remove) this helper improving plugp100 library
class TapoHelper:
    def __init__(self, host, username, password):
        self.p100 = P100(host)
        self.username = username
        self.password = password
        self.device_info = {}

    def setup(self) -> bool:
        try:
            state = self.get_state()
            self.device_info = {
                "device_id": state["device_id"],
                "nickname": state["nickname"],
                "model": state["model"],
                "type": state["type"],
            }
            return True
        except Exception as error:
            _LOGGER.error(f"setup failed: {error}")
            return False

    def check_connection(self) -> bool:
        try:
            self.p100.handshake()
            self.p100.login_request(self.username, self.password)
            return True
        except ResponseErrorCodeNotZero as error:
            _LOGGER.error(f"Non zero response: {error}")
            return False
        except Exception as error:
            _LOGGER.error(f"Unexpected error: {error}")
            return False

    def change_state(self, state: bool):
        return self.__try_or_reconnect(
            lambda: self.p100.change_state(int(state), "88-00-DE-AD-52-E1")
        )

    def get_state(self) -> Dict[str, any]:
        return self.__try_or_reconnect(self.p100.get_state)

    def get_device_id(self) -> str:
        return self.device_info["device_id"]

    def get_device_name(self) -> str:
        return base64.b64decode(self.device_info["nickname"]).decode("utf-8")

    def get_model(self) -> str:
        return self.device_info["model"]

    def get_type(self) -> str:
        return self.device_info["type"]

    def __try_or_reconnect(self, callback):
        try:
            return callback()
        except Exception:  # TODO: identify the connection expired error
            if self.check_connection():
                return callback()