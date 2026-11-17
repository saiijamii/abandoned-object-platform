from typing import Any, Callable

from .sources import FramePacket


class PassthroughProcessor:
    """No-op hook. Replace with Phase Three adapter in runtime deployment."""

    def __call__(self, packet: FramePacket) -> list[Any]:
        return []


def passthrough_factory(_camera) -> Callable[[FramePacket], Any]:
    return PassthroughProcessor()
