#!/usr/bin/env python3
import os
import glob
import urllib.parse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

def build_advanced_excel_report():
    print("[+] Initializing Intelligent Excel Reporter Engine...")
    
    # 1. 마스터 타깃 목록 로드 (탭 분할 기준점)
    if not os.path.exists('targets.txt'):
        print("[-] Error: targets.txt missing.")
        return
        
    with open('targets.txt', 'r') as f:
        targets = [line.strip() for line in f if line.strip()]

    # 도메인별 데이터 구조화: { 도메인: set((URL, 도구)) } -> 중복 제거용
    matrix_data = {domain: set() for domain in targets}

    # 2. 12대 가상머신이 복호화해 둔 results/ 폴더 내 모든 파일 전수조사
    txt_files = glob.glob('results/**/*.*', recursive=True) + glob.glob('results/*.*')
    txt_files = [f for f in txt_files if os.path.isfile(f)]

    if not txt_files:
        print("[-] Warning: No decrypted text files found in results/ folder.")
        return

    print(f"[+] Processing {len(txt_files)} data source files...")
    
    for file_path in txt_files:
        filename = os.path.basename(file_path).lower()
        
        # 파일명에서 소스 엔진 도구 식별
        if 'secretfinder' in filename:
            source_tool = 'SecretFinder'
        elif 'waybackurls' in filename:
            source_tool = 'Waybackurls'
        elif 'gau' in filename:
            source_tool = 'GAU'
        else:
            source_tool = 'Combined-Engine'

        # 파일 내용 라인별 스캔
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    url = line.strip()
                    if not url or url.startswith('#'):
                        continue
                    
                    # 해당 URL이 65개 마스터 도메인 중 어디에 속하는지 분류 매핑
                    for domain in targets:
                        if domain in url:
                            matrix_data[domain].add((url, source_tool))
                            break
        except Exception as e:
            print(f"[-] Error reading {filename}: {e}")

    # 3. 고품격 엑셀 문서 작성 디자인 빌드
    wb = Workbook()
    # 기본 생성되는 첫 시트 제거 준비
    default_sheet = wb.active

    # 스타일 시트 에셋 정의 (가독성 극대화)
    font_header = Font(name='Malgun Gothic', size=11, bold=True, color='FFFFFF')
    font_body = Font(name='Malgun Gothic', size=10, bold=False)
    fill_header = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid') # 신뢰감을 주는 딥블루
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    sheets_created = 0

    for domain, dataset in matrix_data.items():
        if not dataset:
            continue  # 데이터가 한 건도 없는 도메인은 탭 생성 패스
            
        # 깃허브 탭 이름 제한(최대 31자) 조율 및 시트 생성
        safe_tab_name = domain[:30]
        ws = wb.create_sheet(title=safe_tab_name)
        sheets_created += 1

        # 헤더 라인 라벨링
        headers = ["No", "Target URL / Endpoint (수집된 자산 주소)", "Source Tool (발견 도구)"]
        ws.append(headers)

        # 헤더 디자인 튜닝
        ws.row_dimensions[1].height = 26
        for col_num, header_text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center

        # 정렬된 데이터 쓰기 (도구별, URL별로 보기 좋게 사전 정렬)
        sorted_dataset = sorted(list(dataset), key=lambda x: (x[1], x[0]))
        
        for idx, (url, tool) in enumerate(sorted_dataset, 1):
            ws.append([idx, url, tool])
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 20
            
            # 본문 스타일 주입
            ws.cell(row=current_row, column=1).font = font_body
            ws.cell(row=current_row, column=1).alignment = align_center
            
            ws.cell(row=current_row, column=2).font = font_body
            ws.cell(row=current_row, column=2).alignment = align_left
            
            ws.cell(row=current_row, column=3).font = font_body
            ws.cell(row=current_row, column=3).alignment = align_center

        # [🔥핵심 고도화]: 이 탭의 데이터 전체 영역에 '엑셀 자동 필터' 장착
        max_row = ws.max_row
        max_col_letter = get_column_letter(ws.max_column)
        ws.auto_filter.ref = f"A1:{max_col_letter}{max_row}"

        # 컬럼 너비 지능형 자동 맞춤
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    # 한글/대문자 폭을 고려한 대략적인 글자 길이 산정
                    max_len = max(max_len, len(str(cell.value)))
            # 너비 제한 밸런스 패치 (최소 10, 최대 90)
            ws.column_dimensions[col_letter].width = max(min(max_len + 3, 90), 10)

    # 4. 마무리 및 마스터 파일 저장
    if sheets_created > 0:
        wb.remove(default_sheet) # 빈 첫 시트 삭제
        os.makedirs('reports', exist_ok=True)
        report_path = 'reports/passive_recon_report_v1.xlsx'
        wb.save(report_path)
        print(f"[+] [SUCCESS] Advanced filtered report generated at: {report_path}")
    else:
        print("[-] Error: Scan results were empty. Excel file not created.")

if __name__ == '__main__':
    build_advanced_excel_report()
