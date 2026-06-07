#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/4 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

scan_jsluice() {
    local domain=$(echo "$1" | xargs)
    [[ -z "$domain" || "$domain" =~ ^# ]] && return

    echo "[+] [$domain] [jsluice Matrix Worker] Discovering JS targets via gau..."
    # 타겟 도메인의 JS 파일 목록 추출 (최대 100개)
    echo "$domain" | gau 2>/dev/null | grep -E '\.js($|\?)' 2>/dev/null | head -n 100 > "results/${domain}_js_temp.txt"

    if [ -s "results/${domain}_js_temp.txt" ]; then
        echo "[+] [$domain] [jsluice Matrix Worker] Analyzing streams in memory (Anti-WAF)..."
        
        # 파일 목록을 한 줄씩 읽어가며 처리
        while read -r url; do
            # [핵심 매커니즘]: 디스크에 파일을 쓰지 않고 curl로 받은 데이터를 jsluice로 다이렉트 패스
            # -A 옵션으로 브라우저 위장, 딜레이를 주어 안전하게 수집
            curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "$url" 2>/dev/null | jsluice urls 2>/dev/null >> "results/${domain}_jsluice_raw.json"
            sleep 0.5
        done < "results/${domain}_js_temp.txt"
        
        # jsluice가 뱉어낸 JSON 결과물에서 깔끔하게 URL 경로만 추출하여 엑셀 가동 포맷으로 복원
        if [ -s "results/${domain}_jsluice_raw.json" ]; then
            cat "results/${domain}_jsluice_raw.json" | jq -r '.url' 2>/dev/null | sort -u > "results/${domain}_linkfinder.txt"
            rm -f "results/${domain}_jsluice_raw.json"
        fi
    else
        echo "  -> [$domain] No JS assets found."
    fi
    rm -f "results/${domain}_js_temp.txt"
}

export -f scan_jsluice
echo "[*] Starting Dynamic Matrix jsluice Scanner for $TARGET_FILE..."
xargs -P 5 -n 1 -a "$TARGET_FILE" -I {} bash -c 'scan_jsluice "{}"'

rm -f targets_group*
