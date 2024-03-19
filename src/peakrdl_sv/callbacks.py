from __future__ import annotations

from typing import Callable
from typing import Coroutine

WriteCallback = Callable[[int, int, int], None]
AsyncWriteCallback = Callable[[int, int, int], Coroutine[None, None, None]]
ReadCallback = Callable[[int, int, int], int]
AsyncReadCallback = Callable[[int, int, int], Coroutine[None, None, int]]


class CallbackSet:
    """Class to hold a set of callbacks, this reduces the number of callback that need
    to be passed around

        :param write_callback: write regardless of space, defaults to None
        :type write_callback: WriteCallback | None, optional
        :param async_write_callback: write and block if no space, defaults to None
        :type async_write_callback: AsyncWriteCallback | None, optional
        :param read_callback: read regardless of emptyness, defaults to None
        :type read_callback: ReadCallback | None, optional
        :param async_read_callback: read and block if empty, defaults to None
        :type async_read_callback: AsyncReadCallback | None, optional
    """

    __slots__ = [
        "_write_callback",
        "_async_write_callback",
        "_read_callback",
        "_async_read_callback",
    ]

    def __init__(
        self,
        write_callback: WriteCallback | None = None,
        async_write_callback: AsyncWriteCallback | None = None,
        read_callback: ReadCallback | None = None,
        async_read_callback: AsyncReadCallback | None = None,
    ):
        self._write_callback = write_callback
        self._async_write_callback = async_write_callback
        self._read_callback = read_callback
        self._async_read_callback = async_read_callback

    @property
    def write_callback(self) -> WriteCallback | None:
        """single non-blocking write callback function

        :return: call back function
        :rtype: Optional[WriteCallback]
        """
        return self._write_callback

    @property
    def async_write_callback(self) -> AsyncWriteCallback | None:
        """single blocking write callback function

        :return: call back function
        :rtype: Optional[AsyncWriteCallback]
        """
        return self._async_write_callback

    @property
    def read_callback(self) -> ReadCallback | None:
        """single non-blocking read callback function

        :return: call back function
        :rtype: Optional[ReadCallback]
        """
        return self._read_callback

    @property
    def async_read_callback(self) -> AsyncReadCallback | None:
        """single blocking read callback function

        :return: call back function
        :rtype: Optional[AsyncReadCallback]
        """
        return self._async_read_callback
