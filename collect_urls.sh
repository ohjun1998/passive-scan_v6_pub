#!/bin/bash
mkdir -p results
GROUP_SUFFIX=$1

split -d -n l/20 targets.txt targets_group
TARGET_FILE="targets_group${GROUP_SUFFIX}"

collect_master() {
    local raw_domain=$(echo "$1" | xargs)
    [[ -z "$raw_domain" || "$raw_domain" =~ ^# ]] && return

    local base_domain="$raw_domain"
    local safe_domain="$raw_domain"
    local regex="^https?://${raw_domain//./\.}(/|$)"

    if [[ "$raw_domain" == \** ]]; then
        base_domain="${raw_domain#\*.}"
        safe_domain="wild_${base_domain}"
        regex="^https?://([a-zA-Z0-9.-]+\.)?${base_domain//./\.}(/|$)"
        echo "[+] [${raw_domain}] 🔍 와일드카드 감지: Subfinder로 서브도메인을 전수조사한 후 아카이빙을 진행합니다."
        
        subfinder -d "$base_domain" -all -silent > "results/${safe_domain}_subs.txt"
        echo "$base_domain" >> "results/${safe_domain}_subs.txt"
        sort -u "results/${safe_domain}_subs.txt" -o "results/${safe_domain}_subs.txt"
        
        local sub_count=$(wc -l < "results/${safe_domain}_subs.txt")
        echo "  -> [Subfinder] 총 ${sub_count}개의 서브도메인을 발견했습니다."
        
        cat "results/${safe_domain}_subs.txt" | gau > "results/${safe_domain}_gau.txt" 2>/dev/null
        cat "results/${safe_domain}_subs.txt" | waybackurls > "results/${safe_domain}_waybackurls.txt" 2>/dev/null
    else
        echo "[+] [${raw_domain}] 🔍 단일 도메인 정찰을 시작합니다."
        echo "$base_domain" | gau > "results/${safe_domain}_gau.txt" 2>/dev/null
        echo "$base_domain" | waybackurls > "results/${safe_domain}_waybackurls.txt" 2>/dev/null
    fi

    grep -iE "$regex" "results/${safe_domain}_gau.txt" | sort -u -o "results/${safe_domain}_gau.txt"
    grep -iE "$regex" "results/${safe_domain}_waybackurls.txt" | sort -u -o "results/${safe_domain}_waybackurls.txt"

    # JS 파일만 추출
    cat "results/${safe_domain}_gau.txt" "results/${safe_domain}_waybackurls.txt" 2>/dev/null | grep -E '\.js($|\?)' 2>/dev/null | sort -u > "results/${safe_domain}_js_raw_list.txt"
    
    # URL을 절대 경로로 모두 변환
    > "results/${safe_domain}_js_master_list.txt"
    while read -r url; do
        [[ -z "$url" ]] && continue
        if [[ "$url" =~ ^https?:// ]]; then echo "$url"
        elif [[ "$url" =~ ^// ]]; then echo "https:$url"
        elif [[ "$url" =~ ^/ ]]; then echo "https://$base_domain$url"
        else echo "https://$base_domain/$url"
        fi
    done < "results/${safe_domain}_js_raw_list.txt" | sort -u > "results/${safe_domain}_js_master_list.txt"

    local total_js=$(wc -l < "results/${safe_domain}_js_master_list.txt")
    echo "  -> [성공] 총 ${total_js}개의 자바스크립트(JS) 소스 경로를 식별했습니다."

    if [ "$total_js" -gt 0 ]; then
        # 💡 [핵심 패치] 이전에 다운로드한 JS 파일을 완벽하게 필터링하여 제외시킵니다.
        if [ -f "global_js_db.txt" ]; then
            sort -u global_js_db.txt -o global_js_db_sorted.txt
            comm -23 "results/${safe_domain}_js_master_list.txt" global_js_db_sorted.txt > "results/${safe_domain}_js_new_list.txt"
        else
            cp "results/${safe_domain}_js_master_list.txt" "results/${safe_domain}_js_new_list.txt"
        fi

        local total_new_js=$(wc -l < "results/${safe_domain}_js_new_list.txt")
        echo "  -> [신규 JS 필터링] 과거 분석 이력을 제외한 ${total_new_js}개의 새로운 JS 파일을 우선 타겟으로 확정했습니다."

        if [ "$total_new_js" -gt 0 ]; then
            local download_dir="results/${safe_domain}_js_files"
            mkdir -p "$download_dir"
            rm -f "results/${safe_domain}_js_mapping.txt"

            # 남은 신규 JS들을 무작위 셔플한 뒤 1000개를 뽑습니다.
            shuf "results/${safe_domain}_js_new_list.txt" | head -n 1000 > "results/${safe_domain}_js_urls_target.txt"
            local target_count=$(wc -l < "results/${safe_domain}_js_urls_target.txt")
            
            echo "  -> [스텔스 다운로드] 셔플된 신규 타겟 ${target_count}개를 가져옵니다..."
            local success_cnt=0
            local fail_cnt=0
            local current=0

            while read -r url; do
                [[ -z "$url" ]] && continue
                ((current++))
                local safe_name=$(echo "$url" | sed 's/[^a-zA-Z0-9]/_/g' | cut -c 1-150).js
                
                # 💡 다운로드에 "성공"한 경우에만 매핑 파일에 기록하여 다음번에 제외되도록 함
                if curl -s -L --connect-timeout 1 --max-time 4 --fail \
                     -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
                     "$url" -o "$download_dir/$safe_name"; then
                    echo "    [✓] (${current}/${target_count}) 다운로드 성공"
                    echo -e "${safe_name}\t${url}" >> "results/${safe_domain}_js_mapping.txt"
                    ((success_cnt++))
                else
                    echo "    [✗] (${current}/${target_count}) 다운로드 실패 (재도전 대기)"
                    ((fail_cnt++))
                fi
                sleep 0.2
            done < "results/${safe_domain}_js_urls_target.txt"

            echo "  -> [작업 완료] 신규 파일 실물 확보: ${success_cnt}개 (실패/막힘: ${fail_cnt}개)"
        else
            echo "  -> [알림] 새로운 JS 파일이 없어 다운로드를 생략합니다. (모두 이미 분석 완료됨)"
        fi
    fi
}

export -f collect_master
echo "[*] 할당된 그룹($TARGET_FILE)에 대한 분산 수집을 시작합니다."
xargs -P 5 -n 1 -a "$TARGET_FILE" -I {} bash -c 'collect_master "{}"'

rm -f targets_group*
