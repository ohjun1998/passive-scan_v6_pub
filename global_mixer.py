#!/usr/bin/env python3
import os
import glob
import re
import random
from urllib.parse import urlparse

def make_absolute(url, domain):
    if url.startswith('http://') or url.startswith('https://'): return url
    elif url.startswith('//'): return f"https:{url}"
    elif url.startswith('/'): return f"https://{domain}{url}"
    else: return f"https://{domain}/{url}"

def run_mixer():
    print("[+] Starting Global Shuffle & Chunker Engine...")
    if not os.path.exists('targets.txt'): return
    
    with open('targets.txt', 'r') as f:
        targets = [line.strip() for line in f if line.strip()]

    # URL 복원용 매핑 테이블 로드
    js_url_converter = {}
    for mf in glob.glob('results/*_js_mapping.txt'):
        try:
            with open(mf, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if '\t' in line:
                        s, o = line.strip().split('\t', 1)
                        js_url_converter[s] = o
        except: pass

    all_urls = set()
    txt_files = glob.glob('results/**/*.*', recursive=True) + glob.glob('results/*.*')
    
    for file_path in txt_files:
        if not os.path.isfile(file_path): continue
        filename = os.path.basename(file_path).lower()
        match = re.match(r'^(.*)_(linkfinder|trufflehog|gau|waybackurls)\.txt$', filename)
        if not match: continue
        domain = match.group(1)
        if domain not in targets: continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str or line_str.startswith('#'): continue
                    line_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', line_str)
                    if not line_str: continue

                    if '\t' in line_str: raw_url = line_str.split('\t', 1)[1]
                    else: raw_url = line_str

                    abs_url = make_absolute(raw_url, domain)
                    parsed_netloc = urlparse(abs_url).netloc.split(':')[0]
                    if parsed_netloc == domain:
                        all_urls.add(abs_url)
        except: pass

    # 정적 데이터 네트워크 낭비 차단 필터
    junk_exts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.woff', '.woff2', '.ico', '.eot', '.ttf', '.mp4')
    valid_targets = []
    
    for u in all_urls:
        if not urlparse(u).path.lower().endswith(junk_exts):
            valid_targets.append(u)

    # 🚀 [천재적 전술] 도메인 경계를 완전히 무너뜨리고 30만개 전체 타겟을 뒤섞음 (Global Shuffle)
    random.shuffle(valid_targets)
    print(f"[+] Total core verifiable URLs after global shuffle: {len(valid_targets)}")

    # 20대 타격 노드가 동시 난사할 수 있도록 청크 파일 분배
    os.makedirs('chunks', exist_ok=True)
    num_chunks = 20
    
    if len(valid_targets) == 0:
        for i in range(num_chunks): open(f'chunks/chunk_{i:02d}.txt', 'w').close()
        return

    chunk_size = (len(valid_targets) + num_chunks - 1) // num_chunks
    for i in range(num_chunks):
        chunk_data = valid_targets[i*chunk_size : (i+1)*chunk_size]
        with open(f'chunks/chunk_{i:02d}.txt', 'w') as f:
            for url in chunk_data: f.write(url + '\n')
        print(f"  -> Generated chunks/chunk_{i:02d}.txt : {len(chunk_data)} tokens.")

if __name__ == '__main__':
    run_mixer()
