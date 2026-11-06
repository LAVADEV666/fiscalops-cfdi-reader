"""Test-only Expat/ElementTree adapter. This is NOT the browser DOMParser."""
import json
import sys
import xml.etree.ElementTree as ET


def node(element):
    namespace, local = element.tag[1:].split('}', 1) if element.tag.startswith('{') else ('', element.tag)
    return {'localName': local, 'namespaceURI': namespace, 'attrs': element.attrib,
            'children': [node(child) for child in element]}


try:
    result = {'root': node(ET.fromstring(sys.stdin.buffer.read()))}
except ET.ParseError as error:
    result = {'error': str(error)}
sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
