import re
import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_header_footer(doc):
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.85)
        s.right_margin = Inches(0.85)
        
        # Header
        header = s.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("MuTech — MVP 1 Choir Pitch Tracker Checklist")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(120, 120, 120)
        
        # Footer
        footer = s.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("Confidential — For Internal Project Team Use")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(150, 150, 150)

def build_docx(md_path, docx_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    doc = docx.Document()
    add_header_footer(doc)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(30, 41, 59) # Slate 800

    i = 0
    in_code_block = False
    code_lang = ""
    code_lines = []
    flowchart_img = os.path.join(os.path.dirname(md_path), "workflow_flowchart.png")
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Code block handling
        if line.startswith('```'):
            if in_code_block:
                in_code_block = False
                
                # If code block was mermaid, skip if already handled via image or insert image
                if code_lang.lower() == 'mermaid':
                    code_lines = []
                    code_lang = ""
                    i += 1
                    continue

                # Write standard code block table
                code_text = '\n'.join(code_lines)
                table = doc.add_table(rows=1, cols=1)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = table.cell(0, 0)
                set_cell_background(cell, "F1F5F9") # Slate 100
                set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
                
                # Border
                tcPr = cell._tc.get_or_add_tcPr()
                borders = parse_xml(f'''
                    <w:tcBorders {nsdecls("w")}>
                        <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                        <w:left w:val="single" w:sz="24" w:space="0" w:color="0284C7"/>
                        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                        <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                    </w:tcBorders>
                ''')
                tcPr.append(borders)
                
                cp = cell.paragraphs[0]
                cp.paragraph_format.space_before = Pt(2)
                cp.paragraph_format.space_after = Pt(2)
                crun = cp.add_run(code_text)
                crun.font.name = 'Consolas'
                crun.font.size = Pt(8.5)
                crun.font.color.rgb = RGBColor(15, 23, 42)
                doc.add_paragraph().paragraph_format.space_after = Pt(4)
                code_lines = []
                code_lang = ""
            else:
                in_code_block = True
                code_lang = line[3:].strip()
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Markdown image syntax ![alt](path)
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', line.strip())
        if img_match:
            alt_text, img_rel_path = img_match.groups()
            img_full_path = os.path.normpath(os.path.join(os.path.dirname(md_path), img_rel_path))
            if os.path.exists(img_full_path):
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(8)
                p_img.paragraph_format.space_after = Pt(8)
                r_img = p_img.add_run()
                r_img.add_picture(img_full_path, width=Inches(6.6))
                
                if alt_text:
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_cap.paragraph_format.space_before = Pt(0)
                    p_cap.paragraph_format.space_after = Pt(8)
                    r_cap = p_cap.add_run(f"Figure: {alt_text}")
                    r_cap.italic = True
                    r_cap.font.size = Pt(8.5)
                    r_cap.font.color.rgb = RGBColor(100, 116, 139)
                i += 1
                continue
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Horizontal rule
        if line.strip() in ['---', '***', '___']:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            pBdr = parse_xml(f'''
                <w:pBdr {nsdecls("w")}>
                    <w:bottom w:val="single" w:sz="6" w:space="1" w:color="E2E8F0"/>
                </w:pBdr>
            ''')
            p._p.get_or_add_pPr().append(pBdr)
            i += 1
            continue

        # Title (# )
        if line.startswith('# '):
            title_text = line[2:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(title_text)
            run.font.name = 'Calibri'
            run.font.size = Pt(22)
            run.font.bold = True
            run.font.color.rgb = RGBColor(15, 23, 42) # Slate 900
            i += 1
            continue

        # Heading 2 (## )
        if line.startswith('## '):
            h2_text = line[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(h2_text)
            run.font.name = 'Calibri'
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(3, 105, 161) # Ocean blue #0369A1
            # Bottom border
            pBdr = parse_xml(f'''
                <w:pBdr {nsdecls("w")}>
                    <w:bottom w:val="single" w:sz="8" w:space="2" w:color="0284C7"/>
                </w:pBdr>
            ''')
            p._p.get_or_add_pPr().append(pBdr)
            i += 1
            continue

        # Heading 3 (### )
        if line.startswith('### '):
            h3_text = line[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(h3_text)
            run.font.name = 'Calibri'
            run.font.size = Pt(11.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(30, 41, 59)
            i += 1
            continue

        # Blockquote (> )
        if line.startswith('> '):
            quote_lines = []
            while i < len(lines) and lines[i].startswith('> '):
                quote_lines.append(lines[i][2:].strip())
                i += 1
            
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = table.cell(0, 0)
            set_cell_background(cell, "F8FAFC")
            set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
            
            tcPr = cell._tc.get_or_add_tcPr()
            borders = parse_xml(f'''
                <w:tcBorders {nsdecls("w")}>
                    <w:top w:val="none"/>
                    <w:left w:val="single" w:sz="24" w:space="0" w:color="0EA5E9"/>
                    <w:bottom w:val="none"/>
                    <w:right w:val="none"/>
                </w:tcBorders>
            ''')
            tcPr.append(borders)
            
            cp = cell.paragraphs[0]
            cp.paragraph_format.space_before = Pt(2)
            cp.paragraph_format.space_after = Pt(2)
            
            for q_idx, q_line in enumerate(quote_lines):
                if q_idx > 0:
                    cp = cell.add_paragraph()
                    cp.paragraph_format.space_before = Pt(2)
                    cp.paragraph_format.space_after = Pt(2)
                
                # Check for bullet or bold
                add_formatted_text(cp, q_line)
            
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
            continue

        # Markdown Table (| ... |)
        if line.startswith('|') and '|' in line[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Parse table
            rows_data = []
            for t_line in table_lines:
                # Skip divider line |---|---|
                cells = [c.strip() for c in t_line.strip('|').split('|')]
                if all(re.match(r'^:?-+:?$', c) for c in cells if c):
                    continue
                rows_data.append(cells)
            
            if rows_data:
                num_cols = max(len(r) for r in rows_data)
                tbl = doc.add_table(rows=len(rows_data), cols=num_cols)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl.autofit = True
                
                for r_idx, r_data in enumerate(rows_data):
                    for c_idx in range(num_cols):
                        cell_text = r_data[c_idx] if c_idx < len(r_data) else ""
                        cell = tbl.cell(r_idx, c_idx)
                        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
                        
                        # Style borders
                        tcPr = cell._tc.get_or_add_tcPr()
                        bdr = parse_xml(f'''
                            <w:tcBorders {nsdecls("w")}>
                                <w:top w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                                <w:left w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                                <w:bottom w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                                <w:right w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                            </w:tcBorders>
                        ''')
                        tcPr.append(bdr)
                        
                        cp = cell.paragraphs[0]
                        cp.paragraph_format.space_before = Pt(2)
                        cp.paragraph_format.space_after = Pt(2)
                        
                        if r_idx == 0: # Header row
                            set_cell_background(cell, "0F172A") # Slate 900
                            add_formatted_text(cp, cell_text, default_color=RGBColor(255, 255, 255), force_bold=True)
                        else:
                            bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
                            set_cell_background(cell, bg)
                            add_formatted_text(cp, cell_text)
                
                doc.add_paragraph().paragraph_format.space_after = Pt(6)
            continue

        # Checklist item (- [ ] or - [x])
        chk_match = re.match(r'^(\s*)-\s*\[([ xX])\]\s*(.*)$', line)
        if chk_match:
            indent_spaces = len(chk_match.group(1))
            is_checked = chk_match.group(2).lower() == 'x'
            content = chk_match.group(3)
            
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25 + 0.25 * (indent_spaces // 2))
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            
            # Checkbox symbol
            sym = p.add_run("☑  " if is_checked else "☐  ")
            sym.font.name = "Segoe UI Symbol"
            sym.font.size = Pt(11)
            sym.font.bold = True
            sym.font.color.rgb = RGBColor(14, 165, 233) if not is_checked else RGBColor(16, 185, 129)
            
            add_formatted_text(p, content)
            i += 1
            continue

        # Regular bullet list (- or *)
        bullet_match = re.match(r'^(\s*)[-*]\s*(.*)$', line)
        if bullet_match:
            indent_spaces = len(bullet_match.group(1))
            content = bullet_match.group(2)
            
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35 + 0.25 * (indent_spaces // 2))
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            
            sym = p.add_run("• ")
            sym.font.bold = True
            sym.font.color.rgb = RGBColor(100, 116, 139)
            
            add_formatted_text(p, content)
            i += 1
            continue

        # Numbered list (1. or 2.)
        num_match = re.match(r'^(\s*)(\d+\.)\s*(.*)$', line)
        if num_match:
            indent_spaces = len(num_match.group(1))
            num_label = num_match.group(2)
            content = num_match.group(3)
            
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35 + 0.25 * (indent_spaces // 2))
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            
            lbl = p.add_run(f"{num_label} ")
            lbl.font.bold = True
            lbl.font.color.rgb = RGBColor(3, 105, 161)
            
            add_formatted_text(p, content)
            i += 1
            continue

        # Regular paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        add_formatted_text(p, line)
        i += 1

    doc.save(docx_path)
    print(f"Successfully generated {docx_path}!")

def add_formatted_text(paragraph, text, default_color=None, force_bold=False):
    """Parses markdown bold, italic, code, and links within inline text."""
    # Pattern to match bold, inline code, links, math
    pattern = re.compile(r'(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\)|\$.*?\$|\*.*?\*)')
    tokens = pattern.split(text)
    
    for token in tokens:
        if not token:
            continue
        
        # Bold
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            run = paragraph.add_run(token[2:-2])
            run.bold = True
            if default_color:
                run.font.color.rgb = default_color
            else:
                run.font.color.rgb = RGBColor(15, 23, 42)
        # Inline code
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(185, 28, 28) # Reddish-brown for code
        # Math ($...$)
        elif token.startswith('$') and token.endswith('$') and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
            run.font.name = 'Cambria Math'
            run.font.color.rgb = RGBColor(30, 58, 138)
        # Link [text](url)
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            m = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if m:
                link_text, link_url = m.groups()
                run = paragraph.add_run(link_text)
                run.underline = True
                run.font.color.rgb = RGBColor(2, 132, 199) # Blue link
            else:
                run = paragraph.add_run(token)
        # Italic
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(token)
            if force_bold:
                run.bold = True
            if default_color:
                run.font.color.rgb = default_color

if __name__ == '__main__':
    md_file = r'c:\Users\asus\OneDrive\Desktop\Personal\School\DLSU\MuTech\Repo\MuTech\mvp\docs\IMPLEMENTATION_CHECKLIST.md'
    out_docx = r'c:\Users\asus\OneDrive\Desktop\Personal\School\DLSU\MuTech\Repo\MuTech\mvp\docs\IMPLEMENTATION_CHECKLIST.docx'
    build_docx(md_file, out_docx)
