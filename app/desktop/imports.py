"""Worker-only binary import, bounded ZIP streaming/CRC and metadata projection."""
import io
from pathlib import PurePosixPath
import re
import stat
import zipfile
from app.fiscal.ui_adapter import display_date

MAX_FILE = 32*1024*1024
MAX_ENTRY = 8*1024*1024
MAX_ZIP_TOTAL = 128*1024*1024
MAX_ENTRIES = 20_000
UUID = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')


class Cancelled(Exception):
    pass


def checkpoint(cancel):
    if cancel.is_set():
        raise Cancelled()


def entries(data, name, cancel):
    """Yield (entry_name, bytes, error_code); never extract paths to disk."""
    checkpoint(cancel)
    if len(data) > MAX_FILE:
        yield name, None, 'FILE_BYTE_LIMIT'
        return
    if not name.lower().endswith('.zip'):
        yield name, data, None
        return
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > MAX_ENTRIES:
                yield name, None, 'ZIP_ENTRY_COUNT_LIMIT'
                return
            total = 0
            for member in members:
                checkpoint(cancel)
                path = member.filename.replace('\\', '/')
                parts = PurePosixPath(path)
                mode = member.external_attr >> 16
                if parts.is_absolute() or '..' in parts.parts or ':' in path or '\x00' in path or stat.S_ISLNK(mode):
                    yield path, None, 'ZIP_UNSAFE_PATH'
                    continue
                if member.is_dir():
                    continue
                if member.flag_bits & 1:
                    yield path, None, 'ZIP_ENCRYPTED_ENTRY'
                    continue
                if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    yield path, None, 'ZIP_METHOD_UNSUPPORTED'
                    continue
                if not re.search(r'\.(xml|txt|html|htm)$', path, re.I):
                    yield path, None, 'ZIP_ENTRY_TYPE_UNSUPPORTED'
                    continue
                if member.file_size > MAX_ENTRY or member.file_size > max(1, member.compress_size)*200:
                    yield path, None, 'ZIP_ENTRY_SIZE_OR_RATIO_LIMIT'
                    continue
                try:
                    chunks, size = [], 0
                    with archive.open(member) as stream:
                        while True:
                            checkpoint(cancel)
                            chunk = stream.read(min(65536, MAX_ENTRY-size+1))
                            if not chunk:
                                break
                            size += len(chunk)
                            total += len(chunk)
                            if size > MAX_ENTRY or total > MAX_ZIP_TOTAL:
                                raise ValueError('ZIP_ACTUAL_BYTE_LIMIT')
                            chunks.append(chunk)
                    # ZipExtFile validates the CRC while reading, including the final block.
                    yield path, b''.join(chunks), None
                except Cancelled:
                    raise
                except (ValueError, zipfile.BadZipFile, OSError, EOFError, RuntimeError):
                    yield path, None, 'ZIP_CRC_OR_STREAM_REJECTED'
                    if total > MAX_ZIP_TOTAL:
                        return
    except (zipfile.BadZipFile, ValueError, OSError, EOFError):
        yield name, None, 'ZIP_CONTAINER_REJECTED'


def metadata(data):
    """Return None for non-metadata. Invalid UUIDs remain explicit incidents."""
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = data.decode('utf-16')
    else:
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            return None  # XML encoding belongs to the secure XML parser, never forced here.
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    headings = [cell.strip().strip('"') for cell in lines[0].split('~')]
    folded = [key.lower() for key in headings]
    if 'uuid' not in folded or 'rfcemisor' not in folded or 'estatus' not in folded:
        return None
    rows, incidents = [], []
    for index, line in enumerate(lines[1:], 2):
        values = line.split('~')
        if len(values) != len(headings):
            incidents.append(f'METADATA_COLUMNS_LINE_{index}')
            continue
        source = dict(zip(folded, (v.strip().strip('"') for v in values)))
        uuid = source.get('uuid', '')
        if not UUID.fullmatch(uuid):
            incidents.append(f'METADATA_UUID_LINE_{index}')
            continue
        rows.append({'Uuid': uuid.upper(), 'EstatusTexto': {'1': 'VIGENTE', '0': 'CANCELADO'}.get(source['estatus'], 'DESCONOCIDO'),
                     'FechaCancelacion': display_date(source.get('fechacancelacion', '')), 'source': source})
    return rows, incidents
