import logging
import typing

from dataclasses import dataclass, field, replace, asdict

from .utils import unpack

logger = logging.getLogger("isorescue.header")

_OFFSET_HDR = 0x8000
_SZ_HDR = 0x800

_VOL_DSC_BOOT = 0
_VOL_DSC_PRIMARY = 1
_VOL_DSC_SUPPLEMENTARY = 2
_VOL_DSC_PARTITION = 3
_VOL_DSC_TERMINATOR = 255

_FL_HIDDEN = (1 << 0)
_FL_DIR = (1 << 1)
_FL_ASSOCIATED = (1 << 2)
_FL_EXT = (1 << 3)
_FL_USER_ATTR = (1 << 4)
_FL_RES1 = (1 << 5)
_FL_RES2 = (1 << 6)
_FL_NONFINAL = (1 << 7)

@dataclass(kw_only=True)
class RawBuffer:
    raw_buffer: bytes = field(repr=False)
    raw_offset: int = field(default=0)


@dataclass(kw_only=True)
class VolumeDescriptor(RawBuffer):
    type: int
    id: str
    version: int

class FileFlags:
    def __init__(self, flags: int):
        self.hidden = flags & _FL_HIDDEN
        self.isdir = flags & _FL_DIR
        self.associated = flags & _FL_ASSOCIATED
        self.ext = flags & _FL_EXT
        self.user_attr = flags & _FL_USER_ATTR
        self.reserved1 = flags & _FL_RES1
        self.reserved2 = flags & _FL_RES2
        self.nonfinal = flags & _FL_NONFINAL

@dataclass(kw_only=True)
class DirectoryRecord(RawBuffer):
    length: int
    extended_attribute_length: int

    flags: FileFlags

    extent_location: int
    extent_length: int

    id_length: int
    id: bytes


@dataclass(kw_only=True)
class PrimaryVolumeDescriptor(VolumeDescriptor):
    system_id: bytes
    vol_id: bytes

    vol_sz: int
    logical_block_sz: int

    path_tbl_sz: int

    l_tbl_loc: int
    l_tbl_opt_loc: int

    m_tbl_loc: int
    m_tbl_opt_loc: int

    root: DirectoryRecord


@dataclass(kw_only=True)
class PathTable(RawBuffer):
    length: int
    extended_attribute_length: int

    location: int

    parent_dir: int

    id: bytes

def parse_path_tbl(
    buf: bytes,
    tbl_type: str,
) -> PathTable:
    assert tbl_type in {"l", "m"}, "tbl_type must be one of 'l' or 'm'"

    _len = unpack(buf, 0, 1, "@int8", int)
    _ext_attr_rec_len = unpack(buf, 1, 1, "@int8", int)

    _lba_ext = unpack(buf, 2, 4, "@int32_LSB" if tbl_type == "l" else "@int32_MSB", int)
    _parent_dir = unpack(
        buf, 2, 2, "@int16_LSB" if tbl_type == "l" else "@int16_MSB", int
    )

    # assume.
    _id = buf[8:]

    return PathTable(
        raw_buffer=buf,
        length=_len,
        extended_attribute_length=_ext_attr_rec_len,
        location=_lba_ext,
        parent_dir=_parent_dir,
        id=_id,
    )


def parse_directory_record(
    buf: bytes,
) -> DirectoryRecord | None:
    _len = unpack(buf, 0, 1, "@int8", int)
    logger.debug(f"{_len=};")
    if _len == 0:
        return None

    _ext_attr_rec_len = unpack(buf, 1, 1, "@int8", int)

    _lba_ext = unpack(buf, 2, 8, "@int32_LSB-MSB", int)
    _data_len = unpack(buf, 10, 8, "@int32_LSB_MSB", int)

    _flags = unpack(buf, 25, 1, '@int8', int)

    _id_len = unpack(buf, 32, 1, "@int8", int)
    _id = unpack(buf, 33, _id_len, "@strD", bytes)

    logger.debug(
        f"{_len=};"
        f"{_ext_attr_rec_len=};"
        f"offset_hex:{_lba_ext=:02x};"
        f"offset_hex:{_data_len=:02x};"
        f"{_flags=:08b};"
        f"{_id_len=};"
        f"{_id=};"
    )

    return DirectoryRecord(
        raw_buffer=buf,
        length=_len,
        extended_attribute_length=_ext_attr_rec_len,
        flags=FileFlags(_flags),
        extent_location=_lba_ext,
        extent_length=_data_len,
        id_length=_id_len,
        id=_id,
    )


def parse_volume_descriptor(
    buf: bytes,
) -> VolumeDescriptor:
    _typ = unpack(buf, 0, 1, "@int8", int)
    _id = unpack(buf, 1, 5, "@strA", str)
    _version = unpack(buf, 6, 1, "@int8", int)

    return VolumeDescriptor(
        raw_buffer=buf,
        type=_typ,
        id=_id,
        version=_version,
    )


def fill_volume_descriptor(
    dsc: VolumeDescriptor,
) -> VolumeDescriptor:
    if dsc.type == _VOL_DSC_PRIMARY:
        root_record = parse_directory_record(unpack(dsc.raw_buffer, 156, 34, "34s", bytes))
        assert root_record is not None, "expected root_record to not be None"

        return PrimaryVolumeDescriptor(
            **asdict(dsc),
            system_id=unpack(dsc.raw_buffer, 8, 32, "32s", bytes),
            vol_id=unpack(dsc.raw_buffer, 40, 32, "32s", bytes),
            vol_sz=unpack(dsc.raw_buffer, 80, 8, "@int32_LSB-MSB", int),
            logical_block_sz=unpack(dsc.raw_buffer, 128, 4, "@int16_LSB-MSB", int),
            path_tbl_sz=unpack(dsc.raw_buffer, 132, 8, "@int32_LSB-MSB", int),
            l_tbl_loc=unpack(dsc.raw_buffer, 140, 4, "@int32_LSB", int),
            l_tbl_opt_loc=unpack(dsc.raw_buffer, 144, 4, "@int32_LSB", int),
            m_tbl_loc=unpack(dsc.raw_buffer, 148, 4, "@int32_MSB", int),
            m_tbl_opt_loc=unpack(dsc.raw_buffer, 152, 4, "@int32_MSB", int),
            root=replace(root_record, raw_offset=dsc.raw_offset + 156),
        )

    return dsc


def extract_volume_descriptors(
    fp: typing.BinaryIO,
) -> typing.Generator[VolumeDescriptor, None, None]:
    fp.seek(0)
    fp.seek(_OFFSET_HDR)

    while True:
        offset = fp.tell()
        hdr = fp.read(_SZ_HDR)

        dsc = replace(parse_volume_descriptor(hdr), raw_offset=offset)

        logger.debug(
            "vol_descriptor@0x%x, type=%d, id=%s, version=%d",
            dsc.raw_offset,
            dsc.type,
            dsc.id,
            dsc.version,
        )

        yield fill_volume_descriptor(dsc)

        if dsc.type == _VOL_DSC_TERMINATOR:
            break
