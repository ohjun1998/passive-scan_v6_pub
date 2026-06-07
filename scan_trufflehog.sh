#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/4 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

scan_truffle() {
    local domain=$(echo "$1" | xargs)
    [[ -z "$domain" || "$domain" =~ ^# ]] && return

    # 1단계에서 고스란히 상속받은 마스터 JS 주소록 로드
    local master_list="results/${domain}_js_master_list.txt"

    if [ -s "$master_list" ]; then
        echo "[+] [$domain] [Stage 2: TruffleHog Worker] Downloading targeted JS assets (0% Duplicate Recon)..."
        head -n 50 "$master_list" > "results/${domain}_js_urls_temp.txt"
        
        local download_dir="results/${domain}_js_files"
        mkdir -p "$download_dir"
        
        wget -P "$download_dir" \
             -i "results/${domain}_js_urls_temp.txt" \
             --copies=1 --tries=1 \
             --timeout=5 \
             --wait=1 \
             --random-wait \
             --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" 2>/dev/null || true
        
        echo "[+] [$domain] Running TruffleHog verified filesystem scan..."
        trufflehog filesystem "$download_dir" --only-verified --plain 2>/dev/null > "results/${domain}_trufflehog.txt"
        
        # 파일시스템 즉시 청소 및 임시 데이터 파기
        rm -rf "$download_dir"
        rm -f "results/${domain}_js_urls_temp.txt"
    else
        echo "  -> [$domain] No JS assets found from Stage 1 Index."
    fi
}

export -f scan_truffle
echo "[*] Launching Stage 2 TruffleHog Analyzer Matrix for $TARGET_FILE..."
xargs -P 5 -n 1 -a "$TARGET_FILE" -I {} bash -c 'scan_truffle "{}"'

rm -f targets_group*
