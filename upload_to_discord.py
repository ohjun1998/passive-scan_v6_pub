#!/usr/bin/env python3
import os
import glob
import requests
import sys

def upload_and_notify():
    # 1. reports 폴더 내에서 가장 최신 버전의 엑셀 보고서 파일 탐색
    report_dir = "reports"
    search_pattern = os.path.join(report_dir, "passive_recon_report_v*.xlsx")
    files = glob.glob(search_pattern)
    
    if not files:
        print("[-] Error: No report files found in 'reports/' directory.")
        sys.exit(1)
        
    # 가장 최근에 수정/생성된 타깃 파일 동적 매핑
    latest_report = max(files, key=os.path.getmtime)
    file_size_mb = os.path.getsize(latest_report) / (1024 * 1024)
    filename = os.path.basename(latest_report)
    print(f"[+] Found latest report: {filename} ({file_size_mb:.2f} MB)")

    # 2. GitHub Secrets 인프라로부터 디스코드 웹훅 환경 변수 수혈
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        print("[-] Error: DISCORD_WEBHOOK environment variable is not set in GitHub Actions.")
        sys.exit(1)

    print("[+] Exfiltrating large report using secure 1-time link (file.io)...")
    
    try:
        # 3. file.io 보안 임시 서버로 엑셀 파일 스트리밍 업로드 (최대 2GB 허용)
        # expires=1d 설정으로 다운로드를 안 하더라도 24시간 뒤 자동 폭파 규칙 적용
        upload_url = "https://file.io/?expires=1d"
        with open(latest_report, 'rb') as f:
            upload_response = requests.post(upload_url, files={'file': f}, timeout=90)
        
        if upload_response.status_code != 200:
            print(f"[-] Error: file.io upload failed. Status code: {upload_response.status_code}")
            sys.exit(1)
            
        res_data = upload_response.json()
        
        # 4. 링크 추출 및 디스코드 웹훅용 대시보드 텍스트 조립
        if res_data.get('success'):
            download_link = res_data.get('link')
            print(f"[+] Secure Temporary Link Generated: {download_link}")
            
            # 디스코드 말풍선 레이아웃 정의 (텍스트 전송이므로 413 에러 절대 발생 안 함)
            message = {
                "username": "Ultra Matrix Recon Bot",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/1047/1047711.png",
                "content": (
                    f"🔥 **[Ultra Matrix 정찰 파이프라인 완료]** 🔥\n\n"
                    f"📋 **보고서 파일명:** `{filename}`\n"
                    f"📦 **최종 정제 용량:** `{file_size_mb:.2f} MB` (디스코드 제한 초과로 보안 통로 우회)\n"
                    f"⏰ **링크 유효 기간:** `24시간 후 자동 소멸` 또는 `1회 다운로드 즉시 파괴`\n\n"
                    f"⚠️ *필독 보안 주의사항: 누군가 이 링크를 딱 1번 클릭하여 엑셀을 다운로드하는 즉시 링크가 클라우드에서 영구 폭파됩니다. 두 번 다시 누를 수 없으니 반드시 '본인'만 클릭하여 백업하세요.*\n\n"
                    f"🔗 **보안 다운로드 링크:** {download_link}"
                )
            }
            
            # 5. 디스코드 채널로 파이널 사출 요청
            discord_response = requests.post(webhook_url, json=message, timeout=15)
            
            if discord_response.status_code in [200, 204]:
                print("[+] Dispatched secure link to Discord successfully!")
            else:
                print(f"[-] Discord webhook rejected. Status: {discord_response.status_code}, Res: {discord_response.text}")
                sys.exit(1)
        else:
            print(f"[-] file.io backend returned success=False. Data: {res_data}")
            sys.exit(1)
            
    except Exception as e:
        print(f"[-] Unexpected critical error during exfiltration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    upload_and_notify()
