# Not Starlette's request.form() / MultiPartParser: it keeps whole parts in memory or in its own temporary files with no per-file limit and no way to stop at the first byte over; python-multipart's streaming parser (already pinned in constraints.txt) is what Starlette itself builds on, and this wraps it so a file is written as it arrives and the read stops at the limit.
"""Receiving an upload form (web-upload-page): the bytes of a multipart request are written, as they arrive, into one folder of the platform host.

Nothing here judges a file (names, pairing, the samplesheet, the environment are judged in actions/uploads.py) and nothing opens a connection:
a file part is written to `<incoming>/<n>.part`, whatever it is called, so a name can never choose where it lands; the name is only kept
beside it. A part that is over the limit stops the read at once. Any refusal, and any failure, removes the whole folder.
"""
import os
import re
import time

from python_multipart import MultipartParser
from python_multipart.exceptions import ParseError
from python_multipart.multipart import parse_options_header
from starlette.concurrency import run_in_threadpool

from . import cloud_store

FILE_LIMIT = cloud_store.UPLOAD_LIMIT      # bytes, per file (decimal 2 GB: the same number the queue and the command text use)
SHEET_LIMIT = 1_048_576                    # the samplesheet, 1 MiB (the number of actions/datasets.py SAMPLESHEET_LIMIT)
MAX_FILES = 100
MAX_FIELDS = 20
FIELD_BYTES = 8192
STALE_SECONDS = 86400
_NAME = re.compile(rb'(?:^|;)\s*name="([^"]*)"')
_FILENAME = re.compile(rb'(?:^|;)\s*filename="([^"]*)"')


class Rejected(Exception):
    """The request is refused: `code` is the HTTP status, `kind` says why (too_big, forbidden, sheet_too_big, bad_request, too_many, ...), `info` is more."""

    def __init__(self, code, kind, **info):
        super().__init__(kind)
        self.code, self.kind, self.info = code, kind, info


def incoming_for(area, batch):
    return os.path.join(str(area), ".incoming-" + batch)


def discard(folder):
    """Remove a staging folder and the files in it (best effort; a staging folder holds files only)."""
    try:
        for entry in os.scandir(folder):
            try:
                os.unlink(entry.path)
            except OSError:
                pass
        os.rmdir(folder)
    except OSError:
        pass


def sweep(area, now=None, older=STALE_SECONDS):
    """Remove the staging folders a request left behind long ago (a crash, a power cut). Best effort."""
    now = time.time() if now is None else now
    try:
        names = os.listdir(area)
    except OSError:
        return
    for n in names:
        path = os.path.join(area, n)
        if n.startswith(".incoming-"):
            try:
                if now - os.path.getmtime(path) > older:
                    discard(path)
            except OSError:
                pass


def _write(handle, data):
    handle.write(data)


class _Receiver:
    """The callbacks of the parser. They only decide and count (synchronously); what must touch the disk is queued as `ops` and done off the event loop."""

    def __init__(self, incoming, limit, sheet_limit, before_file):
        self.incoming, self.limit, self.sheet_limit, self.before_file = incoming, limit, sheet_limit, before_file
        self.fields, self.files, self.sheet = {}, [], None
        self.ops = []
        self.ended = False
        self.header_name = self.header_value = b""
        self.headers = {}
        self.part = None      # {"kind": "field"|"file"|"sheet"|"skip", ...}
        self.handle = None
        self.count = 0

    # parser callbacks
    def on_part_begin(self):
        self.headers = {}
        self.header_name = self.header_value = b""
        self.part = None

    def on_header_field(self, data, start, end):
        self.header_name += data[start:end]

    def on_header_value(self, data, start, end):
        self.header_value += data[start:end]

    def on_header_end(self):
        self.headers[self.header_name.strip().lower()] = self.header_value
        self.header_name = self.header_value = b""

    def on_headers_finished(self):
        disposition = self.headers.get(b"content-disposition", b"")
        named = _NAME.search(disposition)
        field = named.group(1).decode("utf-8", "replace") if named else ""
        filed = _FILENAME.search(disposition)
        if filed is None:
            if len(self.fields) >= MAX_FIELDS:
                raise Rejected(400, "bad_request")
            self.part = {"kind": "field", "name": field, "data": bytearray()}
            return
        try:
            filename = filed.group(1).decode("utf-8")
        except UnicodeDecodeError:
            raise Rejected(400, "bad_name", names=[filed.group(1).decode("utf-8", "replace")])
        if filename == "" or field not in ("fastq", "samplesheet"):
            self.part = {"kind": "skip"}      # the browser's empty file box (no file chosen), or a box this form does not have
            return
        if self.before_file is not None:
            self.before_file(dict(self.fields))
        if field == "samplesheet":
            self.part = {"kind": "sheet", "data": bytearray()}
            return
        self.count += 1
        if self.count > MAX_FILES:
            raise Rejected(400, "too_many")
        path = os.path.join(self.incoming, "%d.part" % self.count)
        self.part = {"kind": "file", "name": filename, "tmp": path, "size": 0}
        self.ops.append(("open", path))

    def on_part_data(self, data, start, end):
        part = self.part
        if part is None or part["kind"] == "skip":
            return
        chunk = data[start:end]
        if part["kind"] == "field":
            part["data"] += chunk
            if len(part["data"]) > FIELD_BYTES:
                raise Rejected(400, "bad_request")
        elif part["kind"] == "sheet":
            part["data"] += chunk
            if len(part["data"]) > self.sheet_limit:
                raise Rejected(400, "sheet_too_big")
        else:
            part["size"] += len(chunk)
            if part["size"] > self.limit:
                raise Rejected(413, "too_big", name=part["name"])
            self.ops.append(("write", bytes(chunk)))

    def on_part_end(self):
        part = self.part
        if part is None:
            return
        if part["kind"] == "field":
            self.fields[part["name"]] = bytes(part["data"]).decode("utf-8", "replace")
        elif part["kind"] == "sheet":
            self.sheet = bytes(part["data"])
        elif part["kind"] == "file":
            self.ops.append(("close", None))
            self.files.append({"name": part["name"], "tmp": part["tmp"], "size": part["size"]})
        self.part = None

    def on_end(self):
        self.ended = True

    # disk
    def flush(self):
        """Do the queued disk work in order (called off the event loop)."""
        ops, self.ops = self.ops, []
        for op, arg in ops:
            if op == "open":
                self.handle = open(arg, "wb")
            elif op == "write":
                _write(self.handle, arg)
            elif op == "close" and self.handle is not None:
                self.handle.close()
                self.handle = None

    def abandon(self):
        if self.handle is not None:
            try:
                self.handle.close()
            except OSError:
                pass
            self.handle = None


async def receive(stream, content_type, incoming, *, limit=None, sheet_limit=None, before_file=None):
    """Read a multipart/form-data body from `stream` (an async iterator of bytes) into the folder `incoming`. Returns
    {fields: {name: text}, files: [{name, tmp, size}], samplesheet: bytes or None}. `before_file(fields)` is called before the first byte of any
    file is written, with the text fields seen so far, and may raise Rejected (the page refuses a form with a wrong token before anything is
    written). On any refusal or failure the folder `incoming` is removed and Rejected (or the failure) is raised."""
    limit = FILE_LIMIT if limit is None else limit
    sheet_limit = SHEET_LIMIT if sheet_limit is None else sheet_limit
    kind, options = parse_options_header(content_type or "")
    boundary = options.get(b"boundary") if kind == b"multipart/form-data" else None
    if not boundary:
        raise Rejected(400, "bad_request")
    receiver = _Receiver(incoming, limit, sheet_limit, before_file)
    try:
        os.makedirs(incoming, mode=0o700, exist_ok=True)
        parser = MultipartParser(boundary, {"on_part_begin": receiver.on_part_begin, "on_header_field": receiver.on_header_field,
                                            "on_header_value": receiver.on_header_value, "on_header_end": receiver.on_header_end,
                                            "on_headers_finished": receiver.on_headers_finished, "on_part_data": receiver.on_part_data,
                                            "on_part_end": receiver.on_part_end, "on_end": receiver.on_end})
        async for chunk in stream:
            if chunk:
                try:
                    parser.write(chunk)
                except ParseError:
                    raise Rejected(400, "bad_request")
                if receiver.ops:
                    await run_in_threadpool(receiver.flush)
        parser.finalize()
        if receiver.ops:
            await run_in_threadpool(receiver.flush)
        if not receiver.ended:
            raise Rejected(400, "bad_request")
    except BaseException:
        receiver.abandon()
        discard(incoming)
        raise
    receiver.abandon()
    return {"fields": receiver.fields, "files": receiver.files, "samplesheet": receiver.sheet}
