#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/4 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

scan_jsluice() {
    local domain=$(echo "$1" | xargs)
    [[ -z "$domain" || "$domain" =~ ^# ]] && return

    # 1단계에서 고스란히 상속받은 마스터 JS 주소록 로드
    local master_list="results/${domain}_js_master_list.txt"

    if [ -s "$master_list" ]; then
        echo "[+] [$domain] [Stage 2: jsluice Worker] Sanitizing and preparing JS URLs..."
        
        # [핵심 보완]: jsluice용 curl 요청이 실패하지 않도록 완전한 https:// URL 형태로 강제 복원
        head -n 100 "$master_list" | while read -r url; do
            if [[ "$url" =~ ^https?:// ]]; then
                echo "$url"
            elif [[ "$url" =~ ^// ]]; then
                echo "https:$url"
            elif [[ "$url" =~ ^/ ]]; then
                echo "https://$domain$url"
            else
                echo "https://$domain/$url"
            fi
        done > "results/${domain}_js_urls_clean.txt"

        # 정제된 주소 목록이 존재할 때만 안전하게 스트리밍 분석 진행
        if [ -s "results/${domain}_js_urls_clean.txt" ]; then
            echo "[+] [$domain] Analyzing streaming JS data via jsluice (0% Duplicate Recon)..."
            
            while read -r url; do
                # -L 옵션을 추가하여 혹시 CDN 주소가 리다이렉트되더라도 끝까지 소스코드를 긁어오도록 보완
                curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "$url" 2>/dev/null | jsluice urls 2>/dev/null >> "results/${domain}_jsluice_raw.json"
                sleep 0.5
            done < "results/${domain}_js_urls_clean.txt"
        fi

        # 결과 가공 및 정리
        if [ -s "results/${domain}_jsluice_raw.json" ]; then
            # 기존 엑셀 리포터 호환을 위해 파일명을 _linkfinder.txt 로 복원 사출
            cat "results/${domain}_jsluice_raw.json" | jq -r '.url' 2>/dev/null | sort -u > "results/${domain}_linkfinder.txt"
            rm -f "results/${domain}_jsluice_raw.json"
        else
            echo "  -> [$domain] Warning: jsluice found 0 endpoints. Check target connectivity."
            echo "" > "results/${domain}_linkfinder.txt"
        fi
        
        rm -f "results/${domain}_js_urls_clean.txt"
    else
        echo "  -> [$domain] No JS assets found from Stage 1 Index."
    fi
}

export -f scan_jsluice
echo "[*] Launching Stage 2 jsluice (LinkFinder) Analyzer Matrix for $TARGET_FILE..."
xargs -P 5 -n 1 -a "$TARGET_FILE" -I {} bash -c 'scan_jsluice "{}"'

rm -f targets_group*
