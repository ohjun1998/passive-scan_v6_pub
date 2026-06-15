#!/usr/bin/env python3
import os
import glob
import re
import random
import posixpath
from urllib.parse import urlparse, parse_qsl

def make_absolute(url, domain):
    if url.startswith('http://') or url.startswith('https://'): return url
    elif url.startswith('//'): return f"https:{url}"
    elif url.startswith('/'): return f"https://{domain}{url}"
    else: return f"https://{domain}/{url}"

def get_safe_domain(target):
    return "wild_" + target[2:] if target.startswith('*.') else target

def run_mixer():
    print("[+] 글로벌 셔플 엔진 가동 (스마트 파라미터 & 동적 경로 필터링)...")
    if not os.path.exists('targets.txt'): return
    
    with open('targets.txt', 'r') as f:
        targets = [line.strip() for line in f if line.strip()]

    target_map = {get_safe_domain(t): t for t in targets}

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
        
        safe_domain = match.group(1)
        if safe_domain not in target_map: continue
        
        raw_target = target_map[safe_domain]
        is_wildcard = raw_target.startswith('*.')
        base_domain = raw_target[2:] if is_wildcard else raw_target

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str or line_str.startswith('#'): continue
                    line_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', line_str)
                    if not line_str: continue

                    if '\t' in line_str: raw_url = line_str.split('\t', 1)[1]
                    else: raw_url = line_str

                    abs_url = make_absolute(raw_url, base_domain)
                    parsed_netloc = urlparse(abs_url).netloc.split(':')[0]
                    
                    if is_wildcard:
                        if not (parsed_netloc == base_domain or parsed_netloc.endswith('.' + base_domain)):
                            continue
                    else:
                        if parsed_netloc != base_domain:
                            continue
                            
                    all_urls.add(abs_url)
        except: pass

    junk_exts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.woff', '.woff2', '.ico', '.eot', '.ttf', '.mp4')
    valid_targets = []
    
    # 💡 [진화된 핵심 최적화] 폴더(Directory) + 확장자(Ext) + 쿼리키(Query) 3중 구조 분석
    signature_counts = {}
    
    for u in all_urls:
        parsed = urlparse(u)
        
        if parsed.path.lower().endswith(junk_exts):
            continue
            
        query_keys = tuple(sorted([k for k, v in parse_qsl(parsed.query, keep_blank_values=True)]))
        
        # 경로의 마지막 부분을 변수(해시/ID)로 간주하고 폴더 위치와 확장자만 추출
        # 예: /a/b/c/ei39dnr9.js -> path_dir: '/a/b/c', path_ext: '.js'
        # 예: /api/user/123 -> path_dir: '/api/user', path_ext: ''
        path_dir = posixpath.dirname(parsed.path)
        path_ext = posixpath.splitext(parsed.path)[1]
        
        signature = (parsed.netloc, path_dir, path_ext, query_keys)
        
        # 동일한 구조의 URL이 5개 이상이면 폐기
        if signature_counts.get(signature, 0) >= 5:
            continue
            
        signature_counts[signature] = signature_counts.get(signature, 0) + 1
        valid_targets.append(u)

    random.shuffle(valid_targets)
    print(f"[+] 스마트 필터링 및 글로벌 셔플 완료! 최종 점검 대상: 총 {len(valid_targets)} 개")

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
        print(f"  -> 노드 {i:02d} 배정 완료: {len(chunk_data)} 개의 타겟 할당")

if __name__ == '__main__':
    run_mixer()
