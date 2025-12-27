#!/usr/bin/env python3
"""
여주굿뉴스 부동산 실거래가 자동화 스크립트
국토교통부 실거래가 API를 사용하여 여주시 부동산 거래 정보를 가져와 워드프레스에 발행
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import json
import urllib.parse

# 설정
MOLIT_API_KEY = os.environ.get('MOLIT_API_KEY', '')
WP_URL = os.environ.get('WP_URL', 'https://yeojugoodnews.com')
WP_USER = os.environ.get('WP_USER', '')
WP_APP_PASSWORD = os.environ.get('WP_APP_PASSWORD', '')

# 여주시 법정동 코드 (앞 5자리)
YEOJU_CODE = '41670'

# API URL
APT_TRADE_URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade'


def fetch_apt_trades(lawd_cd: str = YEOJU_CODE, deal_ymd: str = None) -> List[Dict]:
    """아파트 매매 실거래가 조회"""
    if not MOLIT_API_KEY:
        print("Error: MOLIT_API_KEY not set")
        return []
    
    if not deal_ymd:
        deal_ymd = datetime.now().strftime('%Y%m')
    
    params = {
        'serviceKey': MOLIT_API_KEY,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'pageNo': 1,
        'numOfRows': 1000
    }
    
    try:
        response = requests.get(APT_TRADE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text not in ['00', '000']:
            result_msg = root.find('.//resultMsg')
            print(f"API Error: {result_msg.text if result_msg is not None else 'Unknown'}")
            return []
        
        trades = []
        for item in root.findall('.//item'):
            trade = {
                'apt_name': get_text(item, 'aptNm'),
                'deal_amount': get_text(item, 'dealAmount'),
                'build_year': get_text(item, 'buildYear'),
                'deal_year': get_text(item, 'dealYear'),
                'deal_month': get_text(item, 'dealMonth'),
                'deal_day': get_text(item, 'dealDay'),
                'dong': get_text(item, 'umdNm'),
                'jibun': get_text(item, 'jibun'),
                'exclusive_area': get_text(item, 'excluUseAr'),
                'floor': get_text(item, 'floor'),
                'deal_type': get_text(item, 'dealingGbn'),
                'apt_dong': get_text(item, 'aptDong'),
                'rgst_date': get_text(item, 'rgstDate'),
                'sgg_cd': get_text(item, 'sggCd'),
            }
            trades.append(trade)
        
        print(f"✅ {deal_ymd} 아파트 매매 {len(trades)}건 조회")
        return trades
        
    except Exception as e:
        print(f"API Error: {e}")
        return []


def get_text(element, tag: str) -> str:
    el = element.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ''


def parse_deal_amount(amount_str: str) -> int:
    try:
        return int(amount_str.replace(',', '').strip())
    except:
        return 0


def format_price(amount: int) -> str:
    if amount >= 10000:
        억 = amount // 10000
        만 = amount % 10000
        if 만 > 0:
            return f"{억}억 {만:,}"
        return f"{억}억"
    return f"{amount:,}"


def calculate_price_per_area(amount: int, area: float) -> int:
    if area <= 0:
        return 0
    pyeong = area / 3.3058
    return int(amount / pyeong)


def generate_html(trades: List[Dict], year_month: str) -> str:
    year = year_month[:4]
    month = year_month[4:]
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    total_count = len(trades)
    amounts = [parse_deal_amount(t['deal_amount']) for t in trades if parse_deal_amount(t['deal_amount']) > 0]
    avg_price = int(sum(amounts) / len(amounts)) if amounts else 0
    max_price = max(amounts) if amounts else 0
    
    recent_trades = []
    now = datetime.now()
    for t in trades:
        try:
            deal_day = int(t['deal_day']) if t['deal_day'] else 0
            deal_month = int(t['deal_month']) if t['deal_month'] else 0
            deal_year = int(t['deal_year']) if t['deal_year'] else 0
            if deal_day and deal_month and deal_year:
                deal_date = datetime(deal_year, deal_month, deal_day)
                if (now - deal_date).days <= 7:
                    recent_trades.append(t)
        except:
            pass
    
    apt_counts = defaultdict(int)
    for t in trades:
        if t['apt_name']:
            apt_counts[t['apt_name']] += 1
    top_apt = max(apt_counts.items(), key=lambda x: x[1]) if apt_counts else ('', 0)
    top_apt_name = top_apt[0][:10] + '...' if len(top_apt[0]) > 10 else top_apt[0]
    
    html = f'''
<div class="yjre-wrap">
<style>
.yjre-wrap * {{
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}}
.yjre-wrap {{
    font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif !important;
    background: #0f0f0f !important;
    color: #e5e5e5 !important;
    line-height: 1.6 !important;
    padding: 20px !important;
    border-radius: 16px !important;
    max-width: 100% !important;
}}
.yjre-header {{
    background: linear-gradient(135deg, #4a1d6a 0%, #1a0a2e 100%) !important;
    border: 1px solid #6b3d99 !important;
    color: white !important;
    padding: 30px !important;
    border-radius: 16px !important;
    margin-bottom: 24px !important;
}}
.yjre-header h2 {{
    font-size: 26px !important;
    margin: 0 0 8px 0 !important;
    color: white !important;
    border: none !important;
    padding: 0 !important;
}}
.yjre-header .yjre-subtitle {{
    opacity: 0.7 !important;
    font-size: 14px !important;
    color: white !important;
}}
.yjre-stats {{
    display: flex !important;
    gap: 24px !important;
    margin-top: 20px !important;
    flex-wrap: wrap !important;
}}
.yjre-stat-item {{
    text-align: center !important;
}}
.yjre-stat-number {{
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #c084fc !important;
}}
.yjre-stat-label {{
    font-size: 13px !important;
    opacity: 0.7 !important;
    color: white !important;
}}
.yjre-summary-cards {{
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 16px !important;
    margin-bottom: 24px !important;
}}
.yjre-summary-card {{
    background: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 12px !important;
    padding: 20px !important;
}}
.yjre-summary-card .yjre-label {{
    font-size: 13px !important;
    color: #888 !important;
    margin-bottom: 8px !important;
}}
.yjre-summary-card .yjre-value {{
    font-size: 22px !important;
    font-weight: 700 !important;
    color: #fff !important;
}}
.yjre-summary-card .yjre-sub {{
    font-size: 13px !important;
    color: #666 !important;
    margin-top: 4px !important;
}}
.yjre-section-title {{
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #fff !important;
    margin-bottom: 16px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}}
.yjre-section-title .yjre-count {{
    background: #333 !important;
    color: #999 !important;
    padding: 4px 10px !important;
    border-radius: 12px !important;
    font-size: 13px !important;
    font-weight: 400 !important;
}}
.yjre-tap-hint {{
    text-align: center !important;
    padding: 12px !important;
    color: #666 !important;
    font-size: 13px !important;
    margin-bottom: 16px !important;
}}
.yjre-list {{
    display: flex !important;
    flex-direction: column !important;
    gap: 12px !important;
    margin-bottom: 32px !important;
}}
.yjre-card {{
    background: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    cursor: pointer !important;
    -webkit-tap-highlight-color: transparent !important;
    user-select: none !important;
    transition: all 0.2s !important;
}}
.yjre-card:hover {{
    border-color: #555 !important;
}}
.yjre-card-main {{
    padding: 20px !important;
    position: relative !important;
}}
.yjre-expand-icon {{
    position: absolute !important;
    right: 16px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 24px !important;
    height: 24px !important;
    color: #555 !important;
    transition: transform 0.3s !important;
}}
.yjre-card.yjre-expanded .yjre-expand-icon {{
    transform: translateY(-50%) rotate(180deg) !important;
}}
.yjre-header-row {{
    display: flex !important;
    justify-content: space-between !important;
    align-items: flex-start !important;
    margin-bottom: 12px !important;
    padding-right: 30px !important;
}}
.yjre-name {{
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #fff !important;
    margin-bottom: 4px !important;
}}
.yjre-address {{
    font-size: 14px !important;
    color: #888 !important;
}}
.yjre-price {{
    text-align: right !important;
}}
.yjre-price .yjre-amount {{
    font-size: 20px !important;
    font-weight: 700 !important;
    color: #c084fc !important;
}}
.yjre-price .yjre-per-area {{
    font-size: 12px !important;
    color: #666 !important;
    margin-top: 2px !important;
}}
.yjre-summary {{
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 16px !important;
    font-size: 14px !important;
    color: #aaa !important;
}}
.yjre-badge {{
    display: inline-block !important;
    padding: 3px 8px !important;
    border-radius: 10px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    margin-left: 6px !important;
    vertical-align: middle !important;
}}
.yjre-badge-new {{
    background: rgba(74, 222, 128, 0.2) !important;
    color: #4ade80 !important;
    border: 1px solid rgba(74, 222, 128, 0.4) !important;
}}
.yjre-detail {{
    max-height: 0 !important;
    overflow: hidden !important;
    transition: max-height 0.3s ease-out !important;
    background: #141414 !important;
}}
.yjre-card.yjre-expanded .yjre-detail {{
    max-height: 400px !important;
}}
.yjre-detail-inner {{
    padding: 20px !important;
    border-top: 1px solid #252525 !important;
}}
.yjre-detail-grid {{
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 16px !important;
}}
.yjre-detail-item {{
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
}}
.yjre-detail-item .yjre-label {{
    font-size: 12px !important;
    color: #666 !important;
}}
.yjre-detail-item .yjre-value {{
    font-size: 15px !important;
    color: #ccc !important;
}}
.yjre-footer {{
    text-align: center !important;
    padding: 24px !important;
    color: #555 !important;
    font-size: 13px !important;
}}
.yjre-footer a {{
    color: #c084fc !important;
    text-decoration: none !important;
}}
@media (max-width: 600px) {{
    .yjre-header {{
        padding: 20px !important;
    }}
    .yjre-header h2 {{
        font-size: 20px !important;
    }}
    .yjre-stats {{
        gap: 16px !important;
    }}
    .yjre-stat-number {{
        font-size: 22px !important;
    }}
    .yjre-header-row {{
        flex-direction: column !important;
        gap: 12px !important;
    }}
    .yjre-price {{
        text-align: left !important;
    }}
    .yjre-detail-grid {{
        grid-template-columns: 1fr !important;
    }}
    .yjre-summary-cards {{
        grid-template-columns: 1fr !important;
    }}
}}
</style>

<div class="yjre-header">
    <h2>🏠 여주시 부동산 실거래가</h2>
    <p class="yjre-subtitle">{year}년 {month}월 기준 · 국토교통부 실거래가 공개시스템</p>
    <div class="yjre-stats">
        <div class="yjre-stat-item">
            <div class="yjre-stat-number">{total_count}</div>
            <div class="yjre-stat-label">{month}월 거래건수</div>
        </div>
        <div class="yjre-stat-item">
            <div class="yjre-stat-number">{format_price(avg_price)}</div>
            <div class="yjre-stat-label">평균 거래가</div>
        </div>
        <div class="yjre-stat-item">
            <div class="yjre-stat-number">{len(recent_trades)}</div>
            <div class="yjre-stat-label">최근 7일</div>
        </div>
    </div>
</div>

<div class="yjre-summary-cards">
    <div class="yjre-summary-card">
        <div class="yjre-label">최고가 거래</div>
        <div class="yjre-value">{format_price(max_price)}</div>
    </div>
    <div class="yjre-summary-card">
        <div class="yjre-label">최다 거래 단지</div>
        <div class="yjre-value">{top_apt[1]}건</div>
        <div class="yjre-sub">{top_apt_name}</div>
    </div>
</div>

<div class="yjre-section-title">
    최근 거래 내역 <span class="yjre-count">아파트 {total_count}건</span>
</div>

<p class="yjre-tap-hint">📱 거래 내역을 탭하면 상세정보를 볼 수 있습니다</p>

<div class="yjre-list">
'''

    sorted_trades = sorted(trades, key=lambda x: (
        int(x['deal_year'] or 0),
        int(x['deal_month'] or 0),
        int(x['deal_day'] or 0)
    ), reverse=True)

    for trade in sorted_trades[:30]:
        amount = parse_deal_amount(trade['deal_amount'])
        area = float(trade['exclusive_area'] or 0)
        pyeong = round(area / 3.3058, 1)
        price_per_pyeong = calculate_price_per_area(amount, area)
        
        badge_html = ''
        try:
            deal_day = int(trade['deal_day']) if trade['deal_day'] else 0
            deal_month = int(trade['deal_month']) if trade['deal_month'] else 0
            deal_year = int(trade['deal_year']) if trade['deal_year'] else 0
            if deal_day and deal_month and deal_year:
                deal_datetime = datetime(deal_year, deal_month, deal_day)
                if (datetime.now() - deal_datetime).days <= 3:
                    badge_html = '<span class="yjre-badge yjre-badge-new">NEW</span>'
        except:
            pass
        
        floor_str = trade['floor'] if trade['floor'] else '-'
        deal_month_str = trade['deal_month'] if trade['deal_month'] else ''
        deal_day_str = trade['deal_day'] if trade['deal_day'] else ''
        
        html += f'''
<div class="yjre-card" onclick="yjreToggle(this)">
    <div class="yjre-card-main">
        <svg class="yjre-expand-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
        <div class="yjre-header-row">
            <div>
                <div class="yjre-name">{trade['apt_name']}{badge_html}</div>
                <div class="yjre-address">여주시 {trade['dong']} {trade['jibun']}</div>
            </div>
            <div class="yjre-price">
                <div class="yjre-amount">{format_price(amount)}</div>
                <div class="yjre-per-area">평당 {price_per_pyeong:,}만</div>
            </div>
        </div>
        <div class="yjre-summary">
            <span>{area}㎡ ({pyeong}평)</span>
            <span>{floor_str}층</span>
            <span>{deal_month_str}/{deal_day_str} 계약</span>
        </div>
    </div>
    <div class="yjre-detail">
        <div class="yjre-detail-inner">
            <div class="yjre-detail-grid">
                <div class="yjre-detail-item">
                    <span class="yjre-label">전용면적</span>
                    <span class="yjre-value">{area}㎡ ({pyeong}평)</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">거래금액</span>
                    <span class="yjre-value">{format_price(amount)}만원</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">층</span>
                    <span class="yjre-value">{floor_str}층</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">건축년도</span>
                    <span class="yjre-value">{trade['build_year']}년</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">계약일</span>
                    <span class="yjre-value">{trade['deal_year']}.{trade['deal_month']}.{trade['deal_day']}</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">거래유형</span>
                    <span class="yjre-value">{trade['deal_type'] or '중개거래'}</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">법정동</span>
                    <span class="yjre-value">{trade['dong']}</span>
                </div>
                <div class="yjre-detail-item">
                    <span class="yjre-label">평당가</span>
                    <span class="yjre-value">{price_per_pyeong:,}만원</span>
                </div>
            </div>
        </div>
    </div>
</div>
'''

    html += f'''
</div>

<div class="yjre-footer">
    <p>자료 출처: <a href="https://rt.molit.go.kr" target="_blank">국토교통부 실거래가 공개시스템</a></p>
    <p style="margin-top: 8px !important; color: #444 !important;">※ 실거래 신고 후 자료 반영까지 시차가 있을 수 있습니다</p>
    <p style="margin-top: 8px !important;">업데이트: {today}</p>
</div>
</div>

<script>
var yjreTouchStartY = 0;
var yjreTouchMove = false;
document.addEventListener('touchstart', function(e) {{
    yjreTouchStartY = e.touches[0].clientY;
    yjreTouchMove = false;
}}, {{ passive: true }});
document.addEventListener('touchmove', function(e) {{
    if (Math.abs(yjreTouchStartY - e.touches[0].clientY) > 10) {{
        yjreTouchMove = true;
    }}
}}, {{ passive: true }});
function yjreToggle(card) {{
    if (yjreTouchMove) return;
    document.querySelectorAll('.yjre-card.yjre-expanded').forEach(function(c) {{
        if (c !== card) c.classList.remove('yjre-expanded');
    }});
    card.classList.toggle('yjre-expanded');
    if (card.classList.contains('yjre-expanded')) {{
        setTimeout(function() {{
            card.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}, 100);
    }}
}}
</script>
'''

    return html


def post_to_wordpress(title: str, content: str, category_id: int = None) -> bool:
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        print("Warning: WordPress credentials not set")
        output_file = f"realestate_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title></head><body style='background:#000;'>{content}</body></html>")
        print(f"✅ HTML 파일 저장: {output_file}")
        return False
    
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    
    post_data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    if category_id:
        post_data['categories'] = [category_id]
    
    try:
        response = requests.post(
            endpoint,
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ 발행 완료: {result.get('link', 'No link')}")
        return True
    except Exception as e:
        print(f"WordPress Error: {e}")
        return False


def main():
    print("🏠 여주굿뉴스 부동산 실거래가 업데이트 시작...")
    
    current_month = datetime.now().strftime('%Y%m')
    
    trades = fetch_apt_trades(deal_ymd=current_month)
    
    if len(trades) < 10:
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m')
        last_month_trades = fetch_apt_trades(deal_ymd=last_month)
        trades.extend(last_month_trades)
        print(f"📊 지난달 포함 총 {len(trades)}건")
    
    if not trades:
        print("거래 데이터가 없습니다.")
        return
    
    content = generate_html(trades, current_month)
    
    year = current_month[:4]
    month = current_month[4:]
    title = f"[부동산] {year}년 {month}월 여주시 아파트 실거래가 ({len(trades)}건)"
    
    post_to_wordpress(title, content, category_id=137)
    
    print("✅ 완료!")


if __name__ == '__main__':
    main()
