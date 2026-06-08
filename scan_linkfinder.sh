#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/4 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

scan_jsluice() {
    local domain=$(echo "$1" | xargs)
    [[ -z "$domain" || "$domain" =~ ^# ]] && return

    local download_dir="results/${domain}_js_files"

    # 로컬 저장소 확인 후 완전 오프라인 연산 진행
    if [ -d "$download_dir" ] && [ "$(ls -A "$download_dir" 2>/dev/null)" ]; then
        echo "[+] [$domain] [Stage 2: jsluice Offline Worker] Parsing local raw assets..."
        
        rm -f "results/${domain}_jsluice_raw.txt"
        touch "results/${domain}_jsluice_raw.txt"

        for js_file in "$download_dir"/*.js; do
            [ -f "$js_file" ] || continue
            local fname=$(basename "$js_file")
            
            # [기능 추가 핵심] URL 추출 시 소스 파일명을 탭(\t) 문자로 엮어 보존
            jsluice urls "$js_file" 2>/dev/null | jq -r --arg f "$fname" '.url | "\($f)\t\(.)"' >> "results/${domain}_jsluice_raw.txt" || true
        done

        if [ -s "results/${domain}_jsluice_raw.txt" ]; then
            sort -u "results/${domain}_jsluice_raw.txt" > "results/${domain}_linkfinder.txt"
            rm -f "results/${domain}_jsluice_raw.txt"
            echo "  -> [$domain] Analysis complete. Extracted $(wc -l < "results/${domain}_linkfinder.txt") endpoints with source mapping."
        else
            echo "  -> [$domain] Warning: No endpoints discovered from local files."
            echo "" > "results/${domain}_linkfinder.txt"
        fi
    else
        echo "  -> [$domain] No local JS assets available from Stage 1 Index."
        echo "" > "results/${domain}_linkfinder.txt"
    fi
}

export -f scan_jsluice
echo "[*] Launching Stage 2 Offline jsluice (LinkFinder) Analyzer Matrix for $TARGET_FILE..."
xargs -P 10 -n 1 -a "$TARGET_FILE" -I {} bash -c 'scan_jsluice "{}"'

rm -f targets_group*
