from __future__ import annotations

import logging

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Immediate
from cocotb.triggers import RisingEdge
from cocotb_bus.drivers import BusDriver
from cocotbext.axi.axil_channels import AxiLiteBus
from cocotbext.axi.axil_master import AxiLiteMaster

from peakrdl_sv.callbacks import CallbackSet
from peakrdl_sv.regmodel import RegModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: Updgrade to a Transaction Class - currently not supported by the RegModel
class CsrTransaction:
    def __init__(self, addr: int, wdata=None):
        self.addr = addr
        self.wdata = wdata
        self.rdata = 0

    @property
    def is_write(self):
        return self.wdata is not None

    @property
    def re(self):
        return 0 if self.is_write else 1

    @property
    def we(self):
        return 1 if self.is_write else 0


class CsrDriver(BusDriver):
    _signals = ["re", "we", "addr", "rdata", "wdata"]

    def __init__(self, dut, clock, name="reg", **kwargs):
        BusDriver.__init__(self, dut, name, clock, **kwargs)
        self.bus.re.value = 0
        self.bus.we.value = 0
        self.bus.addr.value = 0
        self.bus.wdata.value = 0

    # BusDriver classes have a singular _driver_send async method
    async def _driver_send(self, addr: int, wdata: int | None = None) -> int:
        """Writes a value to a register

        :param addr: Absolute register address to read/write to
        :type addr: int
        :param wdata: Optional write data, if None treats as read, defaults to None
        :type wdata: int | None, optional
        :return: The read data, can be discarded if a write as performed
        :rtype: int
        """
        await RisingEdge(self.clock)
        self.bus.re.value = 1 if wdata is None else 0
        self.bus.we.value = 0 if wdata is None else 1
        self.bus.addr.value = addr
        self.bus.wdata.value = wdata or 0

        await RisingEdge(self.clock)
        self.bus.re.value = 0
        self.bus.we.value = 0

        return self.bus.rdata.value.to_unsigned()


class Testbench:
    def __init__(self, dut, rdl_file: str, debug: bool = False):
        self.dut = dut

        # if reset type is even (0 or 2) then active high
        self.rst_active, self.rst_inactive = (
            (1, 0) if self.dut.ResetType.value.to_unsigned() % 2 == 0 else (0, 1)
        )

        # Initialise hw2reg to zero
        self.dut.hw2reg.value = 0
        self.dut.clk.value = Immediate(0)
        self.dut.rst.value = Immediate(self.rst_active)
        self.dut.s_axil_rvalid.value = Immediate(0)

        self.bus = AxiLiteMaster(
            AxiLiteBus.from_prefix(dut, "s_axil"),
            clock=dut.clk,
            reset=dut.rst,
            reset_active_level=self.rst_active,
        )

        self.clkedge = RisingEdge(self.dut.clk)
        self._log = dut._log

        if debug:
            self._log.setLevel(logging.DEBUG)

        # local copies of parameter values
        self.addr_width = self.dut.AW.value.to_unsigned()
        self.data_width = self.dut.DW.value.to_unsigned()

        self._log.info(
            f"Detected AXI Lite bus with AW={self.addr_width}, DW={self.data_width}"
        )

        async def _write(addr, data):
            return await self.bus.write(
                addr, data.to_bytes(self.data_width // 8, "big")
            )

        async def _read(addr):
            return int.from_bytes(
                await self.bus.read(addr, self.data_width // 8), "big"
            )

        # Register Abstraction Layer - use the same call back for each but are called
        # with different args to indicate read/write
        callbacks = CallbackSet(
            async_write_callback=_write,
            async_read_callback=_read,
        )
        self.RAL = RegModel(rdl_file, callbacks, self._log, debug)

        cocotb.start_soon(Clock(dut.clk, 5, "ns").start())

    async def reset(self) -> None:
        """Resets the DUT to a know state, aware of the active low/high reset"""

        self._log.debug("Resetting DUT")

        self._log.debug(
            f"Reset values: Active = {self.rst_active}, Inactive = {self.rst_inactive}"
        )

        self.dut.rst.value = self.rst_active
        for _ in range(10):
            await self.clkedge
        self.dut.rst.value = self.rst_inactive
        for _ in range(10):
            await self.clkedge
