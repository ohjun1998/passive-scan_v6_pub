#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/4 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

scan_lf() {
    local domain=$(echo "$1" | xargs)
    [[ -z "$domain" || "$domain" =~ ^# ]] && return

    echo "[+] [$domain] [LinkFinder Matrix Worker] Discovering JS targets..."
    # 타겟 도메인의 JS 파일 목록 추출 (최대 100개)
    echo "$domain" | gau 2>/dev/null | grep -E '\.js($|\?)' 2>/dev/null | head -n 100 > "results/${domain}_js_temp.txt"

    if [ -s "results/${domain}_js_temp.txt" ]; then
        echo "[+] [$domain] [LinkFinder Matrix Worker] Parsing JS files for hidden endpoints..."
        # 원격 URL을 LinkFinder에 직접 밀어 넣어 내부 엔드포인트 경로 추출
        xargs -P 2 -I {} sh -c 'python LinkFinder/linkfinder.py -i "{}" -o cli 2>/dev/null' < "results/${domain}_js_temp.txt" > "results/${domain}_linkfinder.txt"
    else
        echo "  -> [$domain] No JS assets found."
    fi
    rm -f "results/${domain}_js_temp.txt"
}

export -f scan_lf
echo "[*] Starting Dynamic Matrix LinkFinder Scanner for $TARGET_FILE..."
xargs -P 10 -n 1 -a "$TARGET_FILE" -I {} bash -c 'scan_lf "{}"'

rm -f targets_group*
