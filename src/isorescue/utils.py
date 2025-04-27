import struct
import typing

T = typing.TypeVar("T")


def unpack(
    buffer: bytes, offset: int, length: int, fmt: str, return_type: typing.Type[T]
) -> T:
    if fmt.startswith("@"):
        if fmt == "@int8":
            fmt = "B"
        elif fmt == "@strA":
            fmt = f"{length}s"
        elif fmt == "@strD":
            fmt = f"{length}s"
        elif fmt == "@int32_LSB-MSB" or fmt == "@int32_LSB_MSB":
            r1 = unpack(buffer, offset + 0, 4, "<I", int)
            r2 = unpack(buffer, offset + 4, 4, ">I", int)

            if r1 != r2:
                raise ValueError(
                    f"mismatched r1, r2 for @int32_LSB-MSB, {buffer[offset : offset + length]}, {r1=:02x}, {r2=:02x}"
                )

            return r1
        elif fmt == "@int16_LSB-MSB" or fmt == "@int16_LSB_MSB":
            r1 = unpack(buffer, offset + 0, 2, "<H", int)
            r2 = unpack(buffer, offset + 2, 2, ">H", int)

            if r1 != r2:
                raise ValueError(
                    f"mismatched r1, r2 for @int16_LSB-MSB, {buffer[offset : offset + length]}, {r1=:02x}, {r2:=02x}"
                )

            return r1
        elif fmt == "@int32_LSB":
            fmt = "<I"
        elif fmt == "@int32_MSB":
            fmt = ">I"
        elif fmt == "@int16_LSB":
            fmt = "<H"
        elif fmt == "@int16_MSB":
            fmt = ">H"
        else:
            raise ValueError(f"unknown format: '{fmt}'")

    (r,) = struct.unpack(fmt, buffer[offset : offset + length])
    return r
