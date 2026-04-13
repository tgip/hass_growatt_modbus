"""Synchronous-only Modbus reader that runs I/O in the event loop executor."""

import asyncio
import inspect
from pymodbus.client import ModbusTcpClient

class ModbusReader:
    """Synchronous Modbus reader using ModbusTcpClient executed in executor."""

    def __init__(self, host, port=502, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client = None

    async def async_connect(self):
        """Create and connect a synchronous client inside the executor."""
        loop = asyncio.get_running_loop()

        def _connect():
            self._client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
            return self._client.connect()

        ok = await loop.run_in_executor(None, _connect)
        if not ok:
            raise ConnectionError(f"Unable to connect to {self.host}:{self.port}")

    async def async_close(self):
        """Close the synchronous client in the executor."""
        if not self._client:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._client.close)
        self._client = None

    async def async_read_register(self, addr, unit=1):
        """Read a single register at addr and return int (or raise on failure)."""
        if not self._client:
            raise RuntimeError("Client not connected")

        loop = asyncio.get_running_loop()

        def _try_reads():
            candidates = []
            for name in ("read_input_registers", "read_holding_registers", "read_registers", "read"):
                fn = getattr(self._client, name, None)
                if fn:
                    candidates.append(fn)

            for fn in candidates:
                for args in ((addr, 1, unit), (addr, 1), (addr, unit), (addr,)):
                    try:
                        res = fn(*args)
                    except Exception:
                        continue
                    if res is None:
                        continue
                    if hasattr(res, "registers") and len(res.registers) > 0:
                        return res.registers[0]
                    if isinstance(res, int):
                        return res
                try:
                    sig = inspect.signature(fn)
                    if "unit" in sig.parameters:
                        try:
                            res = fn(addr, 1, unit=unit)
                        except Exception:
                            continue
                        if res is None:
                            continue
                        if hasattr(res, "registers") and len(res.registers) > 0:
                            return res.registers[0]
                        if isinstance(res, int):
                            return res
                except Exception:
                    continue
            raise RuntimeError(f"No compatible register-read method found for client at addr {addr}")

        return await loop.run_in_executor(None, _try_reads)