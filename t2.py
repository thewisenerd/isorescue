import logging
import sys
import typing

import pycdlib

from isorescue.tracing_io import TracingIO

logging.basicConfig(level=logging.DEBUG)

def main():
    iso = pycdlib.PyCdlib()
    with open("/dev/sr0", "rb", buffering=0) as fp:
        fp = TracingIO(fp)
        iso.open_fp(fp)

    for child in iso.list_children(iso_path="/"):
        print(child.fp_offset, child.get_data_length(), child.file_identifier())

    iso.close()


if __name__ == "__main__":
    main()
