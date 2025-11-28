"""Callback utility classes."""

from __future__ import annotations

from collections.abc import Callable, Coroutine

WriteCallback = Callable[[int, int, int], None]
AsyncWriteCallback = Callable[[int, int, int], Coroutine[None, None, None]]
ReadCallback = Callable[[int, int, int], int]
AsyncReadCallback = Callable[[int, int, int], Coroutine[None, None, int]]


class CallbackSet:
    """Class to hold a set of callbacks."""

    __slots__ = [
        "_async_read_callback",
        "_async_write_callback",
        "_read_callback",
        "_write_callback",
    ]

    def __init__(
        self,
        write_callback: WriteCallback | None = None,
        async_write_callback: AsyncWriteCallback | None = None,
        read_callback: ReadCallback | None = None,
        async_read_callback: AsyncReadCallback | None = None,
    ) -> None:
        """Initialise the callback set.

        Args:
          write_callback(WriteCallback | None, optional): write regardless of space, defaults to None
          async_write_callback(AsyncWriteCallback | None, optional): write and block if no space, defaults to None
          read_callback(ReadCallback | None, optional): read regardless of emptyness, defaults to None
          async_read_callback(AsyncReadCallback | None, optional): read and block if empty, defaults to None

        """  # noqa: E501
        self._write_callback = write_callback
        self._async_write_callback = async_write_callback
        self._read_callback = read_callback
        self._async_read_callback = async_read_callback

    @property
    def write_callback(self) -> WriteCallback | None:
        """Single non-blocking write callback function.

        Returns:
          Optional[WriteCallback]: call back function

        """
        return self._write_callback

    @property
    def async_write_callback(self) -> AsyncWriteCallback | None:
        """Single blocking write callback function.

        Returns:
          Optional[AsyncWriteCallback]: call back function

        """
        return self._async_write_callback

    @property
    def read_callback(self) -> ReadCallback | None:
        """Single non-blocking read callback function.

        Returns:
          Optional[ReadCallback]: call back function

        """
        return self._read_callback

    @property
    def async_read_callback(self) -> AsyncReadCallback | None:
        """Single blocking read callback function.

        Returns:
          Optional[AsyncReadCallback]: call back function

        """
        return self._async_read_callback
