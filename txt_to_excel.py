#!/usr/bin/env python3
import os
import glob
import re
import json
from urllib.parse import urlparse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def escape_formula(value):
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')): return "'" + value
    return value

def make_absolute(url, domain):
    if url.startswith('http://') or url.startswith('https://'): return url
    elif url.startswith('//'): return f"https:{url}"
    elif url.startswith('/'): return f"https://{domain}{url}"
    else: return f"https://{domain}/{url}"

def get_status_color(status):
    status_str = str(status)
    if status_str.startswith('2'): return '28A745' # Green
    if status_str.startswith('3'): return '17A2B8' # Blue
    if status_str.startswith('4'): return 'FD7E14' # Orange
    if status_str.startswith('5'): return 'DC3545' # Red
    if 'Static' in status_str: return 'A8B8D0'     # Gray-Blue
    return '6C757D' # Gray (Dead)

def build_advanced_excel_report():
    print("[+] Loading Fast-Track Excel Compiler...", flush=True)
    if not os.path.exists('targets.txt'): return
    with open('targets.txt', 'r') as f: targets = [line.strip() for line in f if line.strip()]

    js_url_converter = {}
    for mf in glob.glob('results/*_js_mapping.txt'):
        try:
            with open(mf, 'r', errors='ignore') as f:
                for line in f:
                    if '\t' in line:
                        s, o = line.strip().split('\t', 1)
                        js_url_converter[s] = o
        except: pass

    matrix_data = {domain: {} for domain in targets}
    
    # 원천 데이터 파싱 (1, 2단계 결과물)
    for file_path in glob.glob('results/*.*'):
        filename = os.path.basename(file_path).lower()
        match = re.match(r'^(.*)_(linkfinder|trufflehog|gau|waybackurls)\.txt$', filename)
        if not match: continue
        
        current_domain = match.group(1)
        if current_domain not in targets: continue

        if 'linkfinder' in filename or 'jsluice' in filename: source_tool = 'LinkFinder'
        elif 'trufflehog' in filename: source_tool = 'TruffleHog'
        elif 'waybackurls' in filename: source_tool = 'Waybackurls'
        elif 'gau' in filename: source_tool = 'GAU'
        else: continue

        try:
            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str or line_str.startswith('#'): continue
                    line_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', line_str)
                    if not line_str: continue
                    
                    if '\t' in line_str: js_file, raw_url = line_str.split('\t', 1)
                    else: js_file, raw_url = "Passive Archive", line_str
                    
                    if js_file in js_url_converter: js_file = js_url_converter[js_file]
                    
                    abs_url = make_absolute(raw_url, current_domain)
                    parsed_netloc = urlparse(abs_url).netloc.split(':')[0]
                    if parsed_netloc != current_domain: continue 

                    if abs_url not in matrix_data[current_domain]:
                        matrix_data[current_domain][abs_url] = {"tools": set(), "files": set()}
                    matrix_data[current_domain][abs_url]["tools"].add(source_tool)
                    if source_tool in ['LinkFinder', 'TruffleHog']:
                        matrix_data[current_domain][abs_url]["files"].add(js_file)
        except: pass

    # 💡 20대의 Httpx 분산 타격 노드가 회수해온 분산 상태 코드 취합 연동
    status_codes = {}
    for res_file in glob.glob('results/httpx_results_*.json'):
        try:
            with open(res_file, 'r', errors='ignore') as f:
                for line in f:
                    data = json.loads(line.strip())
                    status_codes[data.get('url')] = data.get('status_code', 'Dead')
        except: pass

    junk_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.woff', '.woff2', '.ico', '.eot', '.ttf', '.mp4')

    # ==========================================
    # 엑셀 시트 렌더링 파트
    # ==========================================
    wb = Workbook()
    font_header, fill_header = Font(name='Malgun Gothic', bold=True, color='FFFFFF'), PatternFill(start_color='2F3542', end_color='2F3542', fill_type='solid')
    font_data, fill_zebra = Font(name='Malgun Gothic', size=10, color='333333'), PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
    align_center, align_left = Alignment(horizontal='center', vertical='center'), Alignment(horizontal='left', vertical='center')
    thin_border = Border(left=Side(style="thin", color="E0E0E0"), right=Side(style="thin", color="E0E0E0"), top=Side(style="thin", color="E0E0E0"), bottom=Side(style="thin", color="E0E0E0"))

    ws_dash = wb.active
    ws_dash.title = "Summary Dashboard"
    ws_dash.append(["No", "Target Domain", "Total URLs", "jsluice 추출 개수", "TruffleHog 탐지 개수"])
    for c in range(1, 6): ws_dash.cell(1, c).font = font_header; ws_dash.cell(1, c).fill = fill_header; ws_dash.cell(1, c).alignment = align_center; ws_dash.cell(1, c).border = thin_border

    ws_high = wb.create_sheet(title="High Risk Targets")
    ws_high.append(["No", "Source Tool", "Found in JS File", "Status", "Domain", "High Risk URL / Endpoint", "Risk Reason"]) 
    for c in range(1, 8): ws_high.cell(1, c).font = font_header; ws_high.cell(1, c).fill = fill_header; ws_high.cell(1, c).alignment = align_center; ws_high.cell(1, c).border = thin_border

    high_risk_keywords = ['config', '.env', 'xml', 'json', 'secret', 'api/v', 'token', 'admin', 'password', 'key', 'credential', 'mysql']
    dash_idx, high_risk_idx = 2, 2  

    for domain, url_map in matrix_data.items():
        sheet_title = re.sub(r'[\\/\?\*\:\[\]]', '_', domain)[:30]
        passive_count = sum(1 for data in url_map.values() if 'Waybackurls' in data["tools"] or 'GAU' in data["tools"])
        jsluice_count = sum(1 for data in url_map.values() if 'LinkFinder' in data["tools"])
        trufflehog_count = sum(1 for data in url_map.values() if 'TruffleHog' in data["tools"])
        
        ws_dash.append([dash_idx - 1, escape_formula(domain), passive_count, jsluice_count, trufflehog_count])
        for c in range(1, 6):
            ws_dash.cell(dash_idx, c).font = font_data; ws_dash.cell(dash_idx, c).border = thin_border
            ws_dash.cell(dash_idx, c).alignment = align_left if c == 2 else align_center
            if c == 2 and url_map: ws_dash.cell(dash_idx, c).hyperlink = f"#'{sheet_title}'!A1"; ws_dash.cell(dash_idx, c).font = Font(name='Malgun Gothic', color='0056B3', underline='single')
        dash_idx += 1

        if not url_map: continue

        ws = wb.create_sheet(title=sheet_title)
        ws.append(["No", "Source Tool", "Found in JS File", "Status", "Target Absolute URL"]) 
        for c in range(1, 6): ws.cell(1, c).font = font_header; ws.cell(1, c).fill = fill_header; ws.cell(1, c).alignment = align_center; ws.cell(1, c).border = thin_border

        for sub_idx, (url, data) in enumerate(sorted(url_map.items()), 1):
            if sub_idx > 1048500: break
            tools_str = ", ".join(sorted(list(data["tools"])))
            files_str = ", ".join(sorted(list(data["files"]))) if data["files"] else "-"
            
            if urlparse(url).path.lower().endswith(junk_extensions):
                current_status = "Static(생략)"
            else:
                current_status = status_codes.get(url, 'Dead')
            
            ws.append([sub_idx, escape_formula(tools_str), escape_formula(files_str), current_status, escape_formula(url)]) 
            
            for c in range(1, 6):
                cell = ws.cell(sub_idx + 1, c)
                cell.font = font_data; cell.border = thin_border
                if ((sub_idx + 1) % 2) == 1: cell.fill = fill_zebra
                
                if c == 4:
                    cell.fill = PatternFill(start_color=get_status_color(current_status), end_color=get_status_color(current_status), fill_type='solid')
                    cell.font = Font(name='Malgun Gothic', bold=True, color='FFFFFF'); cell.alignment = align_center
                elif c in [3, 5]: cell.alignment = align_left
                else: cell.alignment = align_center

            # 위협 탐지 필터링
            is_high_risk, reason = False, ""
            if 'TruffleHog' in data["tools"]: is_high_risk, reason = True, "TruffleHog 검증 완료 민감 키(Secret) 유출 징후"
            else:
                matched = [key for key in high_risk_keywords if key in url.lower()]
                if matched: is_high_risk, reason = True, f"민감 키워드 감지 ({', '.join(matched)})"
                    
            if is_high_risk:
                ws_high.append([high_risk_idx - 1, escape_formula(tools_str), escape_formula(files_str), current_status, escape_formula(domain), escape_formula(url), escape_formula(reason)]) 
                for c in range(1, 8):
                    cell = ws_high.cell(high_risk_idx, c)
                    cell.font = font_data; cell.border = thin_border
                    if (high_risk_idx % 2) == 1: cell.fill = fill_zebra
                    if c == 4:
                        cell.fill = PatternFill(start_color=get_status_color(current_status), end_color=get_status_color(current_status), fill_type='solid')
                        cell.font = Font(name='Malgun Gothic', bold=True, color='FFFFFF'); cell.alignment = align_center
                    elif c in [3, 5, 6, 7]: cell.alignment = align_left
                    else: cell.alignment = align_center
                high_risk_idx += 1

    # 가독성 자동 마진 정돈
    for sheet in wb.worksheets:
        for col_idx, col in enumerate(sheet.columns, 1):
            col_letter = get_column_letter(col_idx)
            header = str(sheet.cell(1, col_idx).value)
            if header in ["Target Absolute URL", "High Risk URL / Endpoint"]: sheet.column_dimensions[col_letter].width = 80  
            elif header == "Found in JS File": sheet.column_dimensions[col_letter].width = 50  
            elif header == "Risk Reason": sheet.column_dimensions[col_letter].width = 40  
            elif header == "Status": sheet.column_dimensions[col_letter].width = 14
            else: sheet.column_dimensions[col_letter].width = 18

    ws_dash.column_dimensions['B'].width = 35
    os.makedirs('reports', exist_ok=True)
    wb.save('reports/passive_recon_report_v1.xlsx')
    print("[+] Master Excel Build Complete!")

if __name__ == '__main__':
    build_advanced_excel_report()
