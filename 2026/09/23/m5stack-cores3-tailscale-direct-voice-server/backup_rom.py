"""Read a full flash backup with esptool 5.3 ROM mode and MD5 verification.

Blocks whose device-side MD5 matches erased flash are reconstructed as 0xff.
Every nonempty block is read normally. Finally compare the whole image to the
device's whole-flash MD5 before esptool is allowed to save the backup.
"""
import hashlib

import esptool
from esptool.loader import ESPLoader
from esptool.util import FatalError

original_read = ESPLoader.read_flash


def read_verified(self, offset, length, progress_fn=None):
    if self.IS_STUB:
        raise FatalError("Use --no-stub for this ROM backup helper")
    result = bytearray()
    block_size = 65536
    for position in range(offset, offset + length, block_size):
        size = min(block_size, offset + length - position)
        erased = b"\xff" * size
        device_md5 = self.flash_md5sum(position, size).lower()
        if hashlib.md5(erased).hexdigest() == device_md5:
            data = erased
            mode = "erased (MD5 checked)"
        else:
            data = original_read(self, position, size)
            if hashlib.md5(data).hexdigest() != device_md5:
                raise FatalError(f"MD5 mismatch at {position:#x}")
            mode = "read (MD5 checked)"
        result.extend(data)
        print(f"backup {position + size:#010x}/{offset + length:#010x}: {mode}", flush=True)
    if hashlib.md5(result).hexdigest() != self.flash_md5sum(offset, length).lower():
        raise FatalError("Whole-flash MD5 mismatch; no backup will be saved")
    print("Whole-flash MD5 verified", flush=True)
    return bytes(result)


ESPLoader.read_flash = read_verified
esptool.main()
