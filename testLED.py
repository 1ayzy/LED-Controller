import asyncio
import sys

from bleak import BleakClient

ADDRESS = "A696D3A4-B979-44FA-6313-E4F6EAF2289E"
CHARACTERISTIC = "0000fff3-0000-1000-8000-00805f9b34fb"

POWER_ON = bytearray([0x7E, 0x00, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF])
POWER_OFF = bytearray([0x7E, 0x00, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])


def color_command(r: int, g: int, b: int) -> bytearray:
    return bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF])


async def write(client: BleakClient, payload: bytearray) -> None:
    try:
        await client.write_gatt_char(CHARACTERISTIC, payload, response=False)
    except Exception:
        await client.write_gatt_char(CHARACTERISTIC, payload, response=True)


async def main() -> None:
    address = sys.argv[1] if len(sys.argv) > 1 else ADDRESS
    rgb = [int(v) for v in sys.argv[2:5]] if len(sys.argv) > 4 else [0, 0, 255]
    async with BleakClient(address, timeout=15.0) as client:
        await write(client, POWER_ON)
        await asyncio.sleep(0.2)
        await write(client, color_command(*rgb))
        await asyncio.sleep(0.2)
        await write(client, POWER_ON)
        print(f"Цвет установлен: RGB {tuple(rgb)}")


if __name__ == "__main__":
    asyncio.run(main())