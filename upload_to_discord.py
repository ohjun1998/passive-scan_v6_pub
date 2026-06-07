#!/usr/bin/env python3
import os
import glob
import zipfile
import requests

def upload_report_safe_engine():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("[-] Error: DISCORD_WEBHOOK_URL variable is missing.")
        return

    # 최신 생성된 단일 마스터 엑셀 리포트 탐색
    files = glob.glob('reports/passive_recon_report_v*.xlsx')
    if not files:
        print("[-] Error: No Excel report asset found in reports/ folder.")
        return
    
    latest_file = max(files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    
    # 디스코드 전송 전 ZIP 압축으로 초경량화
    zip_file_name = file_name.replace('.xlsx', '.zip')
    zip_file_path = os.path.join('reports', zip_file_name)
    
    print(f"[+] Compressing {file_name} for maximum transmission efficiency...", flush=True)
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(latest_file, arcname=file_name)
        
    print(f"[+] Transmitting master tabbed workbook packet to Discord...", flush=True)
    with open(zip_file_path, 'rb') as f:
        payload = {
            'content': (
                f"🚀 **[정찰 완료 - 통합 마스터 엑셀 보고서]**\n"
                f"🔒 65개 대상 도메인이 **개별 탭(시트)**으로 완벽히 매핑되어 한 파일에 모였습니다.\n"
                f"📊 첫 번째 `Dashboard`와 `High Risk Targets` 시트를 통해 기밀 유출 징후를 즉시 파악해 보세요!"
            )
        }
        files_payload = {'file': (zip_file_name, f, 'application/zip')}
        response = requests.post(webhook_url, data=payload, files=files_payload)
        
    if response.status_code in [200, 204]:
        print("[+] [SUCCESS] Native single-packet Discord transmission complete!", flush=True)
    else:
        print(f"[-] Discord error code: {response.status_code}, {response.text}", flush=True)

if __name__ == '__main__':
    upload_report_safe_engine()
