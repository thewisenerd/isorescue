import argparse
import collections
import logging
import typing
from dataclasses import replace

from isorescue.parse import (
    extract_volume_descriptors,
    PrimaryVolumeDescriptor,
    parse_path_tbl,
    parse_directory_record,
    DirectoryRecord,
)

from t2 import TracingIO

logger = logging.getLogger("isorescue")

def walk_tree(
    buf: bytes,
) -> typing.Generator[DirectoryRecord, None, None]:
    offset = 0
    while offset < len(buf):
        logger.debug("parse_record: %d [%02x]", offset, offset)
        record = parse_directory_record(buf[offset:])
        logger.debug("record: %s", record)
        if record is None:
            break

        yield record

        offset += record.length


def main_impl(fp: typing.BinaryIO) -> None:
    fp = TracingIO(fp)

    primary_vol_desc: PrimaryVolumeDescriptor | None = None
    for vol_desc in extract_volume_descriptors(fp):
        if isinstance(vol_desc, PrimaryVolumeDescriptor):
            primary_vol_desc = vol_desc

    if primary_vol_desc is None:
        raise ValueError("did not find any primary volume descriptor!")

    logger.debug("primary vol desc: %s", primary_vol_desc)

    fp.seek(primary_vol_desc.logical_block_sz * primary_vol_desc.l_tbl_loc)
    l_tbl = replace(
        parse_path_tbl(buf=fp.read(primary_vol_desc.path_tbl_sz), tbl_type="l"),
        raw_offset=primary_vol_desc.logical_block_sz * primary_vol_desc.l_tbl_loc,
    )

    fp.seek(primary_vol_desc.logical_block_sz * primary_vol_desc.m_tbl_loc)
    m_tbl = replace(
        parse_path_tbl(fp.read(primary_vol_desc.path_tbl_sz), tbl_type="m"),
        raw_offset=primary_vol_desc.logical_block_sz * primary_vol_desc.m_tbl_loc,
    )

    logger.debug("l_tbl: %s", l_tbl)
    logger.debug("m_tbl: %s", m_tbl)

    # TODO: deal with l_tbl_opt, m_tbl_opt

    fp.seek(primary_vol_desc.root.extent_location * primary_vol_desc.logical_block_sz)
    buf = fp.read(primary_vol_desc.root.extent_length)

    dir_queue: collections.deque[DirectoryRecord] = collections.deque()
    for record in walk_tree(buf):
        if record.flags.isdir:
            if record.id == b'\x00' or record.id == b'\x01':
                pass
            else:
                dir_queue.append(record)

    maxdepth = (1 << 12) # 4096;
    while len(dir_queue) > 0 and maxdepth > 0:
        maxdepth -= 1
        logger.info("dq: %s", dir_queue)

        # pop the first
        dir_record = dir_queue.popleft()

        fp.seek(dir_record.extent_location * primary_vol_desc.logical_block_sz)
        buf = fp.read(dir_record.extent_length)

        for record in walk_tree(buf):
            if record.flags.isdir:
                if record.id == b'\x00' or record.id == b'\x01':
                    pass
                else:
                    dir_queue.append(record)

    # iso = pycdlib.PyCdlib()
    # with io.BytesIO(inp) as fp:
    #     iso.open_fp(fp)
    #
    # for child in iso.list_children(iso_path='/'):
    #     print(child.file_identifier())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input", type=str, required=True, help="input file path"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable verbose logging"
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    logging.basicConfig(
        handlers=[ch],
        level=logging.ERROR,
        format="%(levelname)-8s [%(asctime)s.%(msecs)03d] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("args: %s", args)

    input_file = args.input
    with open(input_file, "rb", 0) as fp:
        logger.debug("main_impl: input_file=%s", input_file)
        main_impl(fp)


if __name__ == "__main__":
    main()
