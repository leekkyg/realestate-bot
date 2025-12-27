#!/usr/bin/env python3
"""
여주굿뉴스 부동산 실거래가 자동화 스크립트
국토교통부 실거래가 API - 아파트, 연립다세대, 단독다가구
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

# 설정
MOLIT_API_KEY = os.environ.get('MOLIT_API_KEY', '')
WP_URL = os.environ.get('WP_URL', 'https://yeojugoodnews.com')
WP_USER = os.environ.get('WP_USER', '')
WP_APP_PASSWORD = os.environ.get('WP_APP_PASSWORD', '')

YEOJU_CODE = '41670'

# API URLs
API_URLS = {
    'apt': 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade',
    'villa': 'https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade',
    'house': 'https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade',
}


def fetch_trades(property_type: str, deal_ymd: str) -> List[Dict]:
    """부동산 실거래가 조회"""
    if not MOLIT_API_KEY:
        return []
    
    url = API_URLS.get(property_type)
    if not url:
        return []
    
    params = {
        'serviceKey': MOLIT_API_KEY,
        'LAWD_CD': YEOJU_CODE,
        'DEAL_YMD': deal_ymd,
        'pageNo': 1,
        'numOfRows': 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text not in ['00', '000']:
            return []
        
        trades = []
        for item in root.findall('.//item'):
            trade = {
                'type': property_type,
                'name': get_text(item, 'aptNm') or get_text(item, 'houseNm') or get_text(item, 'mhouseNm') or '',
                'deal_amount': get_text(item, 'dealAmount'),
                'build_year': get_text(item, 'buildYear'),
                'deal_year': get_text(item, 'dealYear'),
                'deal_month': get_text(item, 'dealMonth'),
                'deal_day': get_text(item, 'dealDay'),
                'dong': get_text(item, 'umdNm'),
                'jibun': get_text(item, 'jibun'),
                'area': get_text(item, 'excluUseAr') or get_text(item, 'totFlrAr') or get_text(item, 'plottageAr') or '',
                'floor': get_text(item, 'floor'),
                'deal_type': get_text(item, 'dealingGbn'),
            }
            # 이름이 없으면 법정동으로 대체
            if not trade['name']:
                trade['name'] = f"{trade['dong']} {trade['jibun']}"
            trades.append(trade)
        
        return trades
        
    except Exception as e:
        print(f"API Error ({property_type}): {e}")
        return []


def get_text(element, tag: str) -> str:
    el = element.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ''


def parse_amount(s: str) -> int:
    try:
        return int(s.replace(',', '').strip())
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


def get_type_label(t: str) -> str:
    labels = {'apt': '아파트', 'villa': '연립/다세대', 'house': '단독/다가구'}
    return labels.get(t, t)


def get_type_color(t: str) -> str:
    colors = {'apt': '#c084fc', 'villa': '#60a5fa', 'house': '#4ade80'}
    return colors.get(t, '#c084fc')


def generate_html(all_trades: List[Dict], year_month: str) -> str:
    year = year_month[:4]
    month = year_month[4:]
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 유형별 분류
    apt_trades = [t for t in all_trades if t['type'] == 'apt']
    villa_trades = [t for t in all_trades if t['type'] == 'villa']
    house_trades = [t for t in all_trades if t['type'] == 'house']
    
    total = len(all_trades)
    
    # 통계
    amounts = [parse_amount(t['deal_amount']) for t in all_trades if parse_amount(t['deal_amount']) > 0]
    avg_price = int(sum(amounts) / len(amounts)) if amounts else 0
    max_price = max(amounts) if amounts else 0
    
    html = f'''
<div class="yjre">
<style>
.yjre {{
    font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif !important;
    background: #111 !important;
    color: #e5e5e5 !important;
    padding: 20px !important;
    border-radius: 16px !important;
    line-height: 1.5 !important;
}}
.yjre * {{
    box-sizing: border-box !important;
}}
.yjre-head {{
    background: linear-gradient(135deg, #4a1d6a, #1a0a2e) !important;
    padding: 24px !important;
    border-radius: 14px !important;
    margin-bottom: 20px !important;
}}
.yjre-head h2 {{
    margin: 0 0 6px 0 !important;
    font-size: 22px !important;
    color: #fff !important;
    border: none !important;
    padding: 0 !important;
}}
.yjre-head p {{
    margin: 0 !important;
    font-size: 13px !important;
    color: rgba(255,255,255,0.6) !important;
}}
.yjre-stats {{
    display: flex !important;
    gap: 20px !important;
    margin-top: 16px !important;
    flex-wrap: wrap !important;
}}
.yjre-stat {{
    text-align: center !important;
}}
.yjre-stat strong {{
    display: block !important;
    font-size: 24px !important;
    color: #c084fc !important;
}}
.yjre-stat span {{
    font-size: 12px !important;
    color: rgba(255,255,255,0.6) !important;
}}
.yjre-summary {{
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 12px !important;
    margin-bottom: 20px !important;
}}
.yjre-summary-card {{
    background: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 10px !important;
    padding: 14px !important;
    text-align: center !important;
}}
.yjre-summary-card .num {{
    font-size: 20px !important;
    font-weight: 700 !important;
    color: #fff !important;
}}
.yjre-summary-card .lbl {{
    font-size: 11px !important;
    color: #888 !important;
    margin-top: 4px !important;
}}
.yjre-section {{
    margin-bottom: 24px !important;
}}
.yjre-section-title {{
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #fff !important;
    margin-bottom: 12px !important;
    padding-bottom: 8px !important;
    border-bottom: 1px solid #333 !important;
}}
.yjre-section-title .cnt {{
    font-weight: 400 !important;
    color: #888 !important;
    font-size: 14px !important;
}}
.yjre-list {{
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}}
.yjre-item {{
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    padding: 14px 16px !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 12px !important;
}}
.yjre-item:hover {{
    border-color: #444 !important;
}}
.yjre-item-left {{
    flex: 1 !important;
    min-width: 0 !important;
}}
.yjre-item-name {{
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #fff !important;
    margin-bottom: 4px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
.yjre-item-info {{
    font-size: 12px !important;
    color: #888 !important;
}}
.yjre-item-info span {{
    margin-right: 8px !important;
}}
.yjre-item-right {{
    text-align: right !important;
    flex-shrink: 0 !important;
}}
.yjre-item-price {{
    font-size: 17px !important;
    font-weight: 700 !important;
    color: #c084fc !important;
}}
.yjre-item-price.villa {{
    color: #60a5fa !important;
}}
.yjre-item-price.house {{
    color: #4ade80 !important;
}}
.yjre-item-sub {{
    font-size: 11px !important;
    color: #666 !important;
}}
.yjre-footer {{
    text-align: center !important;
    padding: 16px !important;
    font-size: 12px !important;
    color: #555 !important;
}}
.yjre-footer a {{
    color: #c084fc !important;
}}
.yjre-empty {{
    text-align: center !important;
    padding: 20px !important;
    color: #666 !important;
    font-size: 13px !important;
}}
@media (max-width: 600px) {{
    .yjre-summary {{
        grid-template-columns: repeat(3, 1fr) !important;
    }}
    .yjre-item {{
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 8px !important;
    }}
    .yjre-item-right {{
        text-align: left !important;
        width: 100% !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
    }}
}}
</style>

<div class="yjre-head">
    <h2>🏠 여주시 부동산 실거래가</h2>
    <p>{year}년 {month}월 기준 · 국토교통부</p>
    <div class="yjre-stats">
        <div class="yjre-stat">
            <strong>{total}</strong>
            <span>총 거래</span>
        </div>
        <div class="yjre-stat">
            <strong>{format_price(avg_price)}</strong>
            <span>평균가</span>
        </div>
        <div class="yjre-stat">
            <strong>{format_price(max_price)}</strong>
            <span>최고가</span>
        </div>
    </div>
</div>

<div class="yjre-summary">
    <div class="yjre-summary-card">
        <div class="num" style="color:#c084fc !important;">{len(apt_trades)}</div>
        <div class="lbl">아파트</div>
    </div>
    <div class="yjre-summary-card">
        <div class="num" style="color:#60a5fa !important;">{len(villa_trades)}</div>
        <div class="lbl">연립/다세대</div>
    </div>
    <div class="yjre-summary-card">
        <div class="num" style="color:#4ade80 !important;">{len(house_trades)}</div>
        <div class="lbl">단독/다가구</div>
    </div>
</div>
'''

    # 아파트 섹션
    if apt_trades:
        html += generate_section('아파트', 'apt', apt_trades)
    
    # 연립다세대 섹션
    if villa_trades:
        html += generate_section('연립/다세대', 'villa', villa_trades)
    
    # 단독다가구 섹션
    if house_trades:
        html += generate_section('단독/다가구', 'house', house_trades)
    
    html += f'''
<div class="yjre-footer">
    자료: <a href="https://rt.molit.go.kr" target="_blank">국토교통부 실거래가 공개시스템</a><br>
    업데이트: {today}
</div>
</div>
'''
    return html


def generate_section(title: str, ptype: str, trades: List[Dict]) -> str:
    # 최신순 정렬
    sorted_trades = sorted(trades, key=lambda x: (
        int(x['deal_year'] or 0),
        int(x['deal_month'] or 0),
        int(x['deal_day'] or 0)
    ), reverse=True)[:20]  # 최대 20건
    
    html = f'''
<div class="yjre-section">
    <div class="yjre-section-title">{title} <span class="cnt">({len(trades)}건)</span></div>
    <div class="yjre-list">
'''
    
    for t in sorted_trades:
        amount = parse_amount(t['deal_amount'])
        area = float(t['area']) if t['area'] else 0
        pyeong = round(area / 3.3058, 1) if area else 0
        floor = t['floor'] if t['floor'] else '-'
        deal_date = f"{t['deal_month']}/{t['deal_day']}"
        
        price_class = ptype
        
        html += f'''
        <div class="yjre-item">
            <div class="yjre-item-left">
                <div class="yjre-item-name">{t['name']}</div>
                <div class="yjre-item-info">
                    <span>{t['dong']}</span>
                    <span>{area}㎡({pyeong}평)</span>
                    <span>{floor}층</span>
                    <span>{deal_date}</span>
                </div>
            </div>
            <div class="yjre-item-right">
                <div class="yjre-item-price {price_class}">{format_price(amount)}</div>
            </div>
        </div>
'''
    
    html += '''
    </div>
</div>
'''
    return html


def post_to_wordpress(title: str, content: str, category_id: int = None) -> bool:
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        output_file = f"realestate_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title></head><body style='background:#000;'>{content}</body></html>")
        print(f"✅ HTML 저장: {output_file}")
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
        print(f"✅ 발행 완료: {result.get('link', '')}")
        return True
    except Exception as e:
        print(f"WordPress Error: {e}")
        return False


def main():
    print("🏠 여주굿뉴스 부동산 실거래가 업데이트...")
    
    current_month = datetime.now().strftime('%Y%m')
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m')
    
    all_trades = []
    
    # 아파트
    apt = fetch_trades('apt', current_month)
    if len(apt) < 5:
        apt += fetch_trades('apt', last_month)
    print(f"  아파트: {len(apt)}건")
    all_trades.extend(apt)
    
    # 연립다세대
    villa = fetch_trades('villa', current_month)
    if len(villa) < 5:
        villa += fetch_trades('villa', last_month)
    print(f"  연립/다세대: {len(villa)}건")
    all_trades.extend(villa)
    
    # 단독다가구
    house = fetch_trades('house', current_month)
    if len(house) < 5:
        house += fetch_trades('house', last_month)
    print(f"  단독/다가구: {len(house)}건")
    all_trades.extend(house)
    
    print(f"📊 총 {len(all_trades)}건")
    
    if not all_trades:
        print("거래 데이터 없음")
        return
    
    content = generate_html(all_trades, current_month)
    
    year = current_month[:4]
    month = current_month[4:]
    title = f"[부동산] {year}년 {month}월 여주시 실거래가 ({len(all_trades)}건)"
    
    post_to_wordpress(title, content, category_id=137)
    
    print("✅ 완료!")


if __name__ == '__main__':
    main()
