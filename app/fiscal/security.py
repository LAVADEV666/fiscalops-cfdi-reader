"""Byte-first XML preflight using namespace-aware Expat callbacks, before any normalization."""
from dataclasses import dataclass
import io
import time
from typing import BinaryIO
from xml.parsers import expat


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 8 * 1024 * 1024
    max_depth: int = 64
    max_nodes: int = 100_000
    max_attributes_per_node: int = 128
    max_attribute_chars: int = 1_000_000
    max_text_chars: int = 4_000_000
    max_seconds: float = 5.0


class XmlRejected(ValueError):
    def __init__(self, code: str, *, line: int | None = None, column: int | None = None):
        super().__init__(code)
        self.code, self.line, self.column = code, line, column

    def as_dict(self):
        return {'code': self.code, 'line': self.line, 'column': self.column}


def secure_bytes(source: bytes | BinaryIO, limits: Limits = Limits()) -> tuple[bytes, str]:
    if isinstance(source, bytes):
        if len(source) > limits.max_bytes:
            raise XmlRejected('XML_BYTE_LIMIT')
        stream = io.BytesIO(source)
    elif hasattr(source, 'read'):
        stream = source
    else:
        raise TypeError('XML input must be original bytes or a binary stream')
    parser = expat.ParserCreate(namespace_separator='}')
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    started = time.monotonic()
    depth = nodes = text_chars = size = namespace_declarations = 0
    encoding = 'UTF-8'
    chunks = []

    def reject(code):
        raise XmlRejected(code, line=parser.CurrentLineNumber, column=parser.CurrentColumnNumber)

    def budget():
        if time.monotonic() - started >= limits.max_seconds:
            reject('XML_TIME_LIMIT')

    def declaration(version, declared_encoding, standalone):
        nonlocal encoding
        if version != '1.0':
            reject('XML_VERSION_UNSUPPORTED')
        encoding = declared_encoding or encoding
        if encoding.upper().replace('_', '-') not in ('UTF-8', 'UTF8', 'UTF-16', 'UTF-16LE', 'UTF-16BE', 'ISO-8859-1', 'US-ASCII', 'ASCII'):
            reject('XML_ENCODING_UNSUPPORTED')

    def start(name, attrs):
        nonlocal depth, nodes, namespace_declarations
        budget()
        depth += 1
        nodes += 1
        if depth > limits.max_depth:
            reject('XML_DEPTH_LIMIT')
        if nodes > limits.max_nodes:
            reject('XML_NODE_LIMIT')
        if len(attrs) + namespace_declarations > limits.max_attributes_per_node:
            reject('XML_ATTRIBUTE_LIMIT')
        namespace_declarations = 0
        if any(len(k) + len(v) > limits.max_attribute_chars for k, v in attrs.items()):
            reject('XML_ATTRIBUTE_SIZE_LIMIT')

    def end(name):
        nonlocal depth
        depth -= 1

    def namespace(prefix, uri):
        nonlocal namespace_declarations
        namespace_declarations += 1
        if namespace_declarations > limits.max_attributes_per_node:
            reject('XML_ATTRIBUTE_LIMIT')
        if len(prefix or '') + len(uri or '') > limits.max_attribute_chars:
            reject('XML_ATTRIBUTE_SIZE_LIMIT')

    def text(data):
        nonlocal text_chars
        text_chars += len(data)
        if text_chars > limits.max_text_chars:
            reject('XML_TEXT_LIMIT')
        budget()

    parser.XmlDeclHandler = declaration
    parser.StartElementHandler, parser.EndElementHandler = start, end
    parser.StartNamespaceDeclHandler = namespace
    parser.CharacterDataHandler = text
    parser.StartDoctypeDeclHandler = lambda *args: reject('XML_DTD_FORBIDDEN')
    parser.EntityDeclHandler = lambda *args: reject('XML_ENTITY_FORBIDDEN')
    parser.ExternalEntityRefHandler = lambda *args: reject('XML_EXTERNAL_ENTITY_FORBIDDEN')
    parser.SkippedEntityHandler = lambda *args: reject('XML_ENTITY_FORBIDDEN')
    try:
        while True:
            budget()
            chunk = stream.read(min(65536, limits.max_bytes - size + 1))
            if not isinstance(chunk, bytes):
                raise TypeError('XML stream must return bytes')
            if not chunk:
                break
            size += len(chunk)
            if size > limits.max_bytes:
                reject('XML_BYTE_LIMIT')
            chunks.append(chunk)
            parser.Parse(chunk, False)
        parser.Parse(b'', True)
        budget()
    except expat.ExpatError as exc:
        raise XmlRejected('XML_MALFORMED', line=exc.lineno, column=exc.offset) from exc
    data = b''.join(chunks)
    if data.startswith((b'\xff\xfe', b'\xfe\xff')) and encoding == 'UTF-8':
        encoding = 'UTF-16'
    return data, encoding
