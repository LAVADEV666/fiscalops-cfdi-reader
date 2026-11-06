"""Worker-only CSV/TXT/OOXML generation from authoritative report rows and Decimal strings."""
import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
import re
from xml.sax.saxutils import escape, quoteattr
import zipfile
from .imports import checkpoint

MAX_OUTPUT = 64*1024*1024
DECIMAL = re.compile(r'[+-]?[0-9]+(?:\.[0-9]+)?\Z')
ILLEGAL_XML = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


def safe_text(value):
    text = '' if value is None else str(value)
    return "'"+text if re.match(r'\s*[=+\-@]', text) else text


def column_name(index):
    result = ''
    index += 1
    while index:
        index, rest = divmod(index-1, 26)
        result = chr(65+rest)+result
    return result


def xml_text(value):
    value = '' if value is None else str(value)
    if ILLEGAL_XML.search(value):
        raise ValueError('EXPORT_XML_CONTROL_CHARACTER')
    return escape(value)


def validate_columns(cols):
    if not isinstance(cols, list) or not 1 <= len(cols) <= 1024:
        raise ValueError('EXPORT_COLUMNS_LIMIT')
    if len({c.get('id') for c in cols}) != len(cols):
        raise ValueError('EXPORT_COLUMNS_DUPLICATE')
    for col in cols:
        if not isinstance(col.get('id'), str) or len(col['id']) > 200 or not isinstance(col.get('label', col['id']), str):
            raise ValueError('EXPORT_COLUMN_INVALID')
        if len(col.get('label', '')) > 300:
            raise ValueError('EXPORT_LABEL_LIMIT')


def build_delimited(rows, cols, kind, cancel):
    validate_columns(cols)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\r\n', quoting=csv.QUOTE_ALL)
    if kind == 'csv':
        writer.writerow([c.get('label', c['id']) for c in cols])
    else:
        stream.write('~'.join(c.get('label', c['id']) for c in cols)+'\r\n')
    for row in rows:
        checkpoint(cancel)
        values = [safe_text(row.get(c['id'])) for c in cols]
        if kind == 'csv':
            writer.writerow(values)
        else:
            stream.write('~'.join(v.replace('~', ' ').replace('\r', ' ').replace('\n', ' ') for v in values)+'\r\n')
        if stream.tell() > MAX_OUTPUT:
            raise ValueError('EXPORT_BYTE_LIMIT')
    data = b'\xef\xbb\xbf'+stream.getvalue().encode('utf-8')
    if len(data) > MAX_OUTPUT:
        raise ValueError('EXPORT_BYTE_LIMIT')
    return data


def cell(value, column, row, definition):
    address = column_name(column)+str(row)
    text = '' if value is None else str(value)
    if definition.get('dataType') in ('currency', 'number') and DECIMAL.fullmatch(text):
        decimal = Decimal(text)
        # Excel numbers have 15 significant digits. Preserve larger values as exact text.
        significant = len(''.join(map(str, decimal.as_tuple().digits)).rstrip('0')) if decimal else 1
        if significant <= 15:
            return f'<c r="{address}" s="2"><v>{text}</v></c>'
    return f'<c r="{address}" t="inlineStr"><is><t xml:space="preserve">{xml_text(safe_text(value))}</t></is></c>'


def sheet_xml(rows, cols, cancel):
    validate_columns(cols)
    if len(rows) > 1_048_575:
        raise ValueError('EXPORT_EXCEL_ROW_LIMIT')
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>']
    for i, col in enumerate(cols, 1):
        width = max(10, min(55, round(int(col.get('width', 160))/7.2)))
        parts.append(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
    parts.append('</cols><sheetData><row r="1" ht="24" customHeight="1">')
    for i, col in enumerate(cols):
        parts.append(f'<c r="{column_name(i)}1" s="1" t="inlineStr"><is><t>{xml_text(col.get("label", col["id"]))}</t></is></c>')
    parts.append('</row>')
    size = 0
    for ri, row in enumerate(rows, 2):
        checkpoint(cancel)
        text = f'<row r="{ri}">'+''.join(cell(row.get(c['id']), ci, ri, c) for ci, c in enumerate(cols))+'</row>'
        size += len(text)
        if size > MAX_OUTPUT:
            raise ValueError('EXPORT_WORKSHEET_BYTE_LIMIT')
        parts.append(text)
    parts.append(f'</sheetData><autoFilter ref="A1:{column_name(len(cols)-1)}{len(rows)+1}"/></worksheet>')
    return ''.join(parts)


STYLES = '''<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF4F2D7F"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border/><border><left style="thin"><color rgb="FFD9D9D9"/></left><right style="thin"><color rgb="FFD9D9D9"/></right><top style="thin"><color rgb="FFD9D9D9"/></top><bottom style="thin"><color rgb="FFD9D9D9"/></bottom></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''


def build_workbook(sheets, cancel):
    if not 1 <= len(sheets) <= 32:
        raise ValueError('EXPORT_SHEET_LIMIT')
    output, used, named = io.BytesIO(), set(), []
    for sheet in sheets:
        name = re.sub(r'[\\/?*\[\]:]', ' ', sheet['name']).strip()[:31] or 'Hoja'
        original, counter = name, 2
        while name in used:
            name = original[:27]+' '+str(counter)
            counter += 1
        used.add(name)
        named.append(dict(sheet, name=name))
    ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        types += '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        types += ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(named)+1))+'</Types>'
        archive.writestr('[Content_Types].xml', types)
        archive.writestr('_rels/.rels', f'<Relationships xmlns="{ns}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>')
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        archive.writestr('docProps/core.xml', f'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:creator>FiscalOps V21</dc:creator><cp:lastModifiedBy>FiscalOps V21</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
        titles = ''.join('<vt:lpstr>'+xml_text(sheet['name'])+'</vt:lpstr>' for sheet in named)
        archive.writestr('docProps/app.xml', f'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>FiscalOps V21</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>{len(named)}</vt:i4></vt:variant></vt:vector></HeadingPairs><TitlesOfParts><vt:vector size="{len(named)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts></Properties>')
        workbook = '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        workbook += ''.join(f'<sheet name={quoteattr(s["name"])} sheetId="{i}" r:id="rId{i}"/>' for i, s in enumerate(named, 1))+'</sheets></workbook>'
        archive.writestr('xl/workbook.xml', workbook)
        relations = ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(named)+1))
        relations += f'<Relationship Id="rId{len(named)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        archive.writestr('xl/_rels/workbook.xml.rels', f'<Relationships xmlns="{ns}">{relations}</Relationships>')
        archive.writestr('xl/styles.xml', STYLES)
        for i, sheet in enumerate(named, 1):
            checkpoint(cancel)
            archive.writestr(f'xl/worksheets/sheet{i}.xml', sheet_xml(sheet['rows'], sheet['cols'], cancel))
            if output.tell() > MAX_OUTPUT:
                raise ValueError('EXPORT_BYTE_LIMIT')
    return output.getvalue()
