#!/usr/bin/env python3
import os
import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

def build_advanced_excel_report():
    # [★강제 플러시 튜닝★] flush=True를 주어 깃허브 액션 콘솔에 즉시 글자를 출력합니다.
    print("[+] Initializing Ultra-Fast Regex Excel Reporter Engine...", flush=True)
    
    if not os.path.exists('targets.txt'):
        print("[-] Error: targets.txt missing.", flush=True)
        return
        
    with open('targets.txt', 'r') as f:
        targets = [line.strip() for line in f if line.strip()]

    targets = sorted(targets, key=len, reverse=True)
    domain_pattern = re.compile('(' + '|'.join(map(re.escape, targets)) + ')')

    matrix_data = {domain: set() for domain in targets}

    # [★디스크 탐색 고도화★] glob 엔진을 버리고 리눅스 친화적인 os.walk로 수십만 개 파일 즉시 핑거프린팅
    print("[+] Scanning results/ folder for decrypted data source files...", flush=True)
    txt_files = []
    if os.path.exists('results'):
        for root, dirs, files in os.walk('results'):
            for file in files:
                txt_files.append(os.path.join(root, file))

    total_files = len(txt_files)
    print(f"[+] Total target files found: {total_files}. Starting parallel string match...", flush=True)
    
    file_count = 0
    for file_path in txt_files:
        filename = os.path.basename(file_path).lower()
        file_count += 1
        
        # 50개 파일을 처리할 때마다 가상머신이 살아있음을 화면에 강제로 보고합니다.
        if file_count % 50 == 0 or file_count == 1 or file_count == total_files:
            print(f"    [-->] Progress Monitor: Analyzing file ({file_count}/{total_files}) -> {filename}", flush=True)
        
        if 'secretfinder' in filename:
            source_tool = 'SecretFinder'
        elif 'waybackurls' in filename:
            source_tool = 'Waybackurls'
        elif 'gau' in filename:
            source_tool = 'GAU'
        else:
            source_tool = 'Combined-Engine'

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    url = line.strip()
                    if not url or url.startswith('#'):
                        continue
                    
                    match = domain_pattern.search(url)
                    if match:
                        matched_domain = match.group(1)
                        matrix_data[matched_domain].add((url, source_tool))
        except Exception as e:
            print(f"[-] Error reading {filename}: {e}", flush=True)

    # 3. 고품격 엑셀 문서 디자인 빌드
    print("[+] Compiling structural grid data into Excel sheet matrix...", flush=True)
    wb = Workbook()
    default_sheet = wb.active

    font_header = Font(name='Malgun Gothic', size=11, bold=True, color='FFFFFF')
    font_body = Font(name='Malgun Gothic', size=10, bold=False)
    fill_header = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    sheets_created = 0

    for domain, dataset in matrix_data.items():
        if not dataset:
            continue
            
        safe_tab_name = domain[:30]
        ws = wb.create_sheet(title=safe_tab_name)
        sheets_created += 1

        headers = ["No", "Target URL / Endpoint (수집된 자산 주소)", "Source Tool (발견 도구)"]
        ws.append(headers)

        ws.row_dimensions[1].height = 26
        for col_num, header_text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center

        sorted_dataset = sorted(list(dataset), key=lambda x: (x[1], x[0]))
        
        max_len_no = len("No")
        max_len_url = len("Target URL / Endpoint (수집된 자산 주소)")
        max_len_tool = len("Source Tool (발견 도구)")
        
        for idx, (url, tool) in enumerate(sorted_dataset, 1):
            if idx > 1048500:
                break
                
            ws.append([idx, url, tool])
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 20
            
            ws.cell(row=current_row, column=1).font = font_body
            ws.cell(row=current_row, column=1).alignment = align_center
            ws.cell(row=current_row, column=2).font = font_body
            ws.cell(row=current_row, column=2).alignment = align_left
            ws.cell(row=current_row, column=3).font = font_body
            ws.cell(row=current_row, column=3).alignment = align_center

            max_len_no = max(max_len_no, len(str(idx)))
            max_len_url = max(max_len_url, len(str(url)))
            max_len_tool = max(max_len_tool, len(str(tool)))

        max_row = ws.max_row
        ws.auto_filter.ref = f"A1:C{max_row}"

        ws.column_dimensions['A'].width = max_len_no + 3
        ws.column_dimensions['B'].width = max(min(max_len_url + 3, 90), 10)
        ws.column_dimensions['C'].width = max_len_tool + 3

    if sheets_created > 0:
        wb.remove(default_sheet)
        os.makedirs('reports', exist_ok=True)
        report_path = 'reports/passive_recon_report_v1.xlsx'
        wb.save(report_path)
        print(f"[+] [SUCCESS] Advanced filtered report generated at: {report_path}", flush=True)
    else:
        print("[-] Error: Scan results were empty. Excel file not created.", flush=True)

if __name__ == '__main__':
    build_advanced_excel_report()
