from __future__ import annotations

import logging

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb_bus.drivers import BusDriver

from peakrdl_sv.callbacks import CallbackSet
from peakrdl_sv.regmodel import RegModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: Updgrade to a Transaction Class
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

    def __init__(self, dut, clock, name="csr", **kwargs):
        BusDriver.__init__(self, dut, name, clock, **kwargs)

    # BusDriver classes have a singular _driver_send async method
    async def _driver_send(self, addr: int, wdata: int | None = None):
        """Writes a value to a register

        :param transaction: _description_
        :type transaction: CsrTransaction
        :param sync: _description_
        :type sync: _type_
        """
        await RisingEdge(self.clock)
        self.bus.re.value = 1 if wdata is None else 0
        self.bus.we.value = 0 if wdata is None else 1
        self.bus.addr.value = addr
        self.bus.wdata.value = wdata or 0
        await RisingEdge(self.clock)
        self.bus.re.value = 0
        self.bus.we.value = 0


class Testbench:
    def __init__(self, dut, rdl_file: str, log):
        self.dut = dut
        self.bus = CsrDriver(dut, dut.clk)
        self.clkedge = RisingEdge(dut.clk)

        # local copies of parameter values
        self.addr_width = self.dut.AW
        self.data_width = self.dut.DW

        # Register Abstraction Layer - use the same call back for each but are called
        # with different args to indicate read/write
        callbacks = CallbackSet(
            async_write_callback=self.bus._driver_send,
            async_read_callback=self.bus._driver_send,
        )
        self.RAL = RegModel(rdl_file, callbacks, log)

        # Initialise the bus to something useful - for now assume that the bus is a CSR
        # bus
        dut.rst.setimmediatevalue(0)
        dut.csr_we.setimmediatevalue(0)
        dut.csr_re.setimmediatevalue(0)
        dut.csr_addr.setimmediatevalue(0)
        dut.csr_wdata.setimmediatevalue(0)
        dut.hw2reg.setimmediatevalue(0)

        cocotb.start_soon(Clock(dut.clk, 5, "ns").start())

    async def reset(self) -> None:
        """Resets the DUT to a know state, aware of the ResetType"""
        self.log.info("Resetting DUT")

        # if reset type is even (0 or 2) then active high
        active_value = 1 if self.dut.ResetType.value % 2 == 0 else 0

        self.dut.rst.value = active_value
        for _ in range(10):
            await self.clkedge
        self.dut.rst.value = ~active_value
