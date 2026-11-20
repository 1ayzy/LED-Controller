import asyncio
from typing import List, Optional

from bleak import BleakClient

# ==== Protocol (verified on ELK-BLEDOM) ====

CHARACTERISTIC = "0000fff3-0000-1000-8000-00805f9b34fb"
CONNECT_TIMEOUT = 15.0
WRITE_DELAY = 0.2

POWER_ON = bytearray([0x7E, 0x00, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF])
POWER_OFF = bytearray([0x7E, 0x00, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])


def color_command(r: int, g: int, b: int) -> bytearray:
    return bytearray([0x7E, 0x00, 0x05, 0x03, int(r), int(g), int(b), 0x00, 0xEF])


class LEDStrip:
    """Raw BLE control: same bytes and order as the working TestLED.py."""

    def __init__(self, address: str, name: str = "") -> None:
        self.address = address
        self.name = name or address
        self.client: Optional[BleakClient] = None
        self.characteristic = CHARACTERISTIC
        self.powered = False
        self.rgb: List[int] = [255, 255, 255]
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return bool(self.client and self.client.is_connected)

    async def _drop(self) -> None:
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.disconnect()
            except Exception:
                pass
        self.client = None

    def _pick_characteristic(self) -> str:
        """Prefer fff3, fall back to the first writable characteristic."""
        try:
            services = getattr(self.client, "services", None)
            if services is None:
                return CHARACTERISTIC
            writable = []
            for service in services:
                for char in service.characteristics:
                    if char.uuid.lower() == CHARACTERISTIC:
                        return CHARACTERISTIC
                    if any("write" in prop for prop in char.properties):
                        writable.append(char.uuid)
            return writable[0] if writable else CHARACTERISTIC
        except Exception:
            return CHARACTERISTIC

    async def _connect_locked(self) -> bool:
        if self.connected:
            return True
        if not self.address:
            print("No usable address for this device on this platform")
            return False
        await self._drop()
        try:
            self.client = BleakClient(self.address, timeout=CONNECT_TIMEOUT)
            await self.client.connect()
            self.characteristic = self._pick_characteristic()
            await asyncio.sleep(WRITE_DELAY)
            return self.connected
        except Exception as e:
            print(f"Connection error ({self.address}): {e}")
            await self._drop()
            return False

    async def connect(self) -> bool:
        async with self._lock:
            return await self._connect_locked()

    async def disconnect(self) -> None:
        async with self._lock:
            await self._drop()

    async def _write(self, payload: bytearray) -> bool:
        async with self._lock:
            for _ in range(2):
                if not await self._connect_locked():
                    return False
                try:
                    try:
                        await self.client.write_gatt_char(self.characteristic, payload, response=False)
                    except Exception:
                        await self.client.write_gatt_char(self.characteristic, payload, response=True)
                    return True
                except Exception as e:
                    print(f"Write error ({self.address}): {e}")
                    await self._drop()
            return False

    # ==== Commands ====

    async def power_on(self) -> bool:
        ok = await self._write(POWER_ON)
        if ok:
            self.powered = True
        return ok

    async def power_off(self) -> bool:
        ok = await self._write(POWER_OFF)
        if ok:
            self.powered = False
        return ok

    async def set_color(self, r: int, g: int, b: int) -> bool:
        if not self.powered:
            await self.power_on()
            await asyncio.sleep(WRITE_DELAY)
        ok = await self._write(color_command(r, g, b))
        if ok:
            self.rgb = [int(r), int(g), int(b)]
            await asyncio.sleep(WRITE_DELAY)
            await self._write(POWER_ON)
        return ok

    async def apply_state(self) -> bool:
        """Restore power and color after a reconnect."""
        if not self.powered:
            return True
        if not await self.power_on():
            return False
        await asyncio.sleep(WRITE_DELAY)
        return await self.set_color(*self.rgb)