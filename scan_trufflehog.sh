#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/20 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

scan_truffle() {
    local raw_domain=$(echo "$1" | xargs)
    [[ -z "$raw_domain" || "$raw_domain" =~ ^# ]] && return

    local safe_domain="$raw_domain"
    if [[ "$raw_domain" == \** ]]; then
        safe_domain="wild_${raw_domain#\*.}"
    fi

    local download_dir="results/${safe_domain}_js_files"

    if [ -d "$download_dir" ] && [ "$(ls -A "$download_dir" 2>/dev/null)" ]; then
        echo "[+] [${raw_domain}] [2단계: TruffleHog] 파일 내부 기밀 정보 유출 검사 시작..."
        trufflehog filesystem "$download_dir" --only-verified --json 2>/dev/null > "results/${safe_domain}_trufflehog_raw.json" || true
        
        if [ -s "results/${safe_domain}_trufflehog_raw.json" ]; then
            cat "results/${safe_domain}_trufflehog_raw.json" | jq -r '. | ((.SourceMetadata.Data.Filesystem.file // "unknown.js") | split("/") | last) + "\t[" + (.DetectorName // "Secret") + "] " + ((.Raw // "") | gsub("\n"; " "))' > "results/${safe_domain}_trufflehog.txt" || true
            rm -f "results/${safe_domain}_trufflehog_raw.json"
        else
            echo "" > "results/${safe_domain}_trufflehog.txt"
        fi
    else
        echo "" > "results/${safe_domain}_trufflehog.txt"
    fi
}

export -f scan_truffle
echo "[*] 오프라인 TruffleHog 스캔 가동..."
# 💡 [핵심 방어] 동시 실행 2개로 고정
xargs -P 2 -n 1 -a "$TARGET_FILE" -I {} bash -c 'scan_truffle "{}"'

rm -f targets_group*
