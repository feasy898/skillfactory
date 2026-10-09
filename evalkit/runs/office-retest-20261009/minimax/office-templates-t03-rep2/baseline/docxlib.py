"""Minimal dependency-free .docx writer for GB/T 9704-style Chinese 公文.

Only what these two 文种 need: styled paragraphs, fixed 28pt line grid,
Chinese fonts, centered page-number footer. No tables/images/TOC, so the
document body stays a plain sequence of <w:p> elements.
"""

import zipfile

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'

# --- GB/T 9704-2012 page geometry (twips) -------------------------------------
MARGIN = {"top": 2098, "bottom": 1984, "left": 1588, "right": 1474}
PAGE_W, PAGE_H = 11906, 16838          # A4
LINE = 560                             # fixed 28pt line grid
INDENT = 640                           # 2 chars at 16pt

# --- fonts --------------------------------------------------------------------
ASCII_FONT = "Times New Roman"
FS = "仿宋"    # body, addressee, signature, date, page number
HT = "黑体"    # level-1 heading
KT = "楷体"    # level-2 heading
XBS = "宋体"   # title fallback for 华文小标宋


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def rpr(font=FS, size=32, bold=False):
    b = "<w:b/><w:bCs/>" if bold else ""
    return (
        "<w:rPr>"
        f'<w:rFonts w:ascii="{ASCII_FONT}" w:eastAsia="{font}" '
        f'w:hAnsi="{ASCII_FONT}" w:cs="{ASCII_FONT}"/>'
        f"{b}<w:color w:val=\"000000\"/><w:sz w:val=\"{size}\"/>"
        f'<w:szCs w:val="{size}"/>'
        "</w:rPr>"
    )


def para(text, *, font=FS, size=32, bold=False, align="both",
         first_indent=0, left_indent=0, spacing_before=0, spacing_after=0,
         line=LINE):
    """One paragraph. `line` in twips, fixed rule (GB/T 28pt grid)."""
    ind = ""
    if first_indent or left_indent:
        ind = (f'<w:ind w:firstLineChars="0" w:left="{left_indent}" '
               f'w:firstLine="{first_indent}"/>')
    ppr = (
        "<w:pPr>"
        f'<w:spacing w:before="{spacing_before}" w:after="{spacing_after}" '
        f'w:line="{line}" w:lineRule="exact"/>'
        f"{ind}"
        f'<w:jc w:val="{align}"/>'
        "</w:pPr>"
    )
    run = ""
    if text:
        run = f"<w:r>{rpr(font, size, bold)}<w:t xml:space=\"preserve\">{esc(text)}</w:t></w:r>"
    return f"<w:p>{ppr}{run}</w:p>"


def para_lines(lines, *, font=FS, size=32, bold=False, align="center",
               spacing_before=0, spacing_after=0, line=LINE):
    """One paragraph carrying soft line breaks (`<w:br/>`).

    Used for 公文 titles: GB/T 9704 wants a balanced multi-line title, and a
    naive wrap would strand 1-2 characters on the last line.
    """
    ppr = (
        "<w:pPr>"
        f'<w:spacing w:before="{spacing_before}" w:after="{spacing_after}" '
        f'w:line="{line}" w:lineRule="exact"/>'
        f'<w:jc w:val="{align}"/>'
        "</w:pPr>"
    )
    runs = []
    for i, t in enumerate(lines):
        br = "<w:br/>" if i else ""
        runs.append(f'<w:r>{rpr(font, size, bold)}{br}'
                    f'<w:t xml:space="preserve">{esc(t)}</w:t></w:r>')
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


def title_lines(title, size):
    """Split a 公文 title so no line strands <=2 characters.

    Splits at the 关于 boundary when the title cannot fit on one line.
    """
    text_w = PAGE_W - MARGIN["left"] - MARGIN["right"]
    per_line = text_w // (size * 10)          # half-points -> twips per CJK char
    if len(title) <= per_line:
        return [title]
    if "关于" in title:
        i = title.index("关于") + len("关于")
        head, tail = title[:i], title[i:]
        if head and tail and len(head) <= per_line and len(tail) <= per_line:
            return [head, tail]
    # fall back to a balanced cut at the midpoint
    mid = len(title) // 2
    return [title[:mid], title[mid:]]


def build_docx(path, body_xml, title, footer=True):
    sect = (
        "<w:sectPr>"
        '<w:footerReference w:type="default" r:id="rId3"/>'
        f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/>'
        f'<w:pgMar w:top="{MARGIN["top"]}" w:right="{MARGIN["right"]}" '
        f'w:bottom="{MARGIN["bottom"]}" w:left="{MARGIN["left"]}" '
        'w:header="1021" w:footer="992" w:gutter="0"/>'
        '<w:cols w:space="425"/>'
        f'<w:docGrid w:type="lines" w:linePitch="{LINE}"/>'
        "</w:sectPr>"
    )

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {W} {R}>"
        f"<w:body>{body_xml}{sect}</w:body>"
        "</w:document>"
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:styles {W}>"
        "<w:docDefaults><w:rPrDefault><w:rPr>"
        f'<w:rFonts w:ascii="{ASCII_FONT}" w:eastAsia="{FS}" '
        f'w:hAnsi="{ASCII_FONT}" w:cs="{ASCII_FONT}"/>'
        '<w:sz w:val="32"/><w:szCs w:val="32"/>'
        "</w:rPr></w:rPrDefault>"
        "<w:pPrDefault><w:pPr>"
        f'<w:spacing w:line="{LINE}" w:lineRule="exact"/>'
        "</w:pPr></w:pPrDefault></w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/>'
        f'<w:pPr><w:widowControl/><w:spacing w:line="{LINE}" w:lineRule="exact"/>'
        '<w:jc w:val="both"/></w:pPr>'
        f'<w:rPr><w:rFonts w:ascii="{ASCII_FONT}" w:eastAsia="{FS}" '
        f'w:hAnsi="{ASCII_FONT}"/><w:sz w:val="32"/></w:rPr>'
        "</w:style>"
        "</w:styles>"
    )

    if footer:
        footer_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f"<w:ftr {W} {R}>"
            '<w:p><w:pPr><w:spacing w:line="' + str(LINE) + '" w:lineRule="exact"/>'
            '<w:jc w:val="center"/></w:pPr>'
            f"<w:r>{rpr(FS, 28)}<w:t xml:space=\"preserve\">\u2014 </w:t></w:r>"
            f'<w:r>{rpr(FS, 28)}<w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r>{rpr(FS, 28)}<w:instrText xml:space="preserve"> PAGE \\* MERGEFORMAT </w:instrText></w:r>'
            f'<w:r>{rpr(FS, 28)}<w:fldChar w:fldCharType="separate"/></w:r>'
            f"<w:r>{rpr(FS, 28)}<w:t>1</w:t></w:r>"
            f'<w:r>{rpr(FS, 28)}<w:fldChar w:fldCharType="end"/></w:r>'
            f"<w:r>{rpr(FS, 28)}<w:t xml:space=\"preserve\"> \u2014</w:t></w:r>"
            "</w:p></w:ftr>"
        )
    else:
        footer_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                      f"<w:ftr {W} {R}><w:p/></w:ftr>")

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )

    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
        "</Relationships>"
    )

    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{esc(title)}</dc:title></cp:coreProperties>"
    )
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           "<Application>ooxml-writer</Application></Properties>")

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/footer1.xml", footer_xml)
    return path