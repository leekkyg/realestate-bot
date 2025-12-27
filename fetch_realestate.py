#!/usr/bin/env python3
"""
여주굿뉴스 부동산 실거래가 자동화 스크립트
국토교통부 실거래가 API - 아파트, 연립다세대, 단독다가구, 토지
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
    'land': 'https://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade',
}


def fetch_trades(property_type: str, deal_ymd: str) -> List[Dict]:
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
            # 토지는 필드가 다름
            if property_type == 'land':
                trade = {
                    'type': property_type,
                    'name': get_text(item, 'umdNm') + ' ' + get_text(item, 'jibun'),
                    'deal_amount': get_text(item, 'dealAmount'),
                    'build_year': '',
                    'deal_year': get_text(item, 'dealYear'),
                    'deal_month': get_text(item, 'dealMonth'),
                    'deal_day': get_text(item, 'dealDay'),
                    'dong': get_text(item, 'umdNm'),
                    'jibun': get_text(item, 'jibun'),
                    'area': get_text(item, 'dealArea'),
                    'floor': '',
                    'deal_type': get_text(item, 'dealingGbn'),
                    'land_use': get_text(item, 'landUse'),
                }
            else:
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


def generate_html(all_trades: List[Dict], year_month: str) -> str:
    year = year_month[:4]
    month = year_month[4:]
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    apt_trades = [t for t in all_trades if t['type'] == 'apt']
    villa_trades = [t for t in all_trades if t['type'] == 'villa']
    house_trades = [t for t in all_trades if t['type'] == 'house']
    land_trades = [t for t in all_trades if t['type'] == 'land']
    
    total = len(all_trades)
    amounts = [parse_amount(t['deal_amount']) for t in all_trades if parse_amount(t['deal_amount']) > 0]
    avg_price = int(sum(amounts) / len(amounts)) if amounts else 0
    max_price = max(amounts) if amounts else 0
    
    html = f'''
<div class="yjre">
<style>
.yjre {{
    font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif !important;
    background: #111 !important;
    color: #ddd !important;
    padding: 16px !important;
    border-radius: 12px !important;
    line-height: 1.4 !important;
    font-size: 14px !important;
}}
.yjre * {{ box-sizing: border-box !important; margin: 0 !important; padding: 0 !important; }}
.yjre-head {{
    background: linear-gradient(135deg, #4a1d6a, #1a0a2e) !important;
    padding: 16px !important;
    border-radius: 10px !important;
    margin-bottom: 12px !important;
}}
.yjre-head h2 {{
    font-size: 18px !important;
    color: #fff !important;
    margin-bottom: 4px !important;
    border: none !important;
}}
.yjre-head p {{
    font-size: 11px !important;
    color: rgba(255,255,255,0.5) !important;
}}
.yjre-stats {{
    display: flex !important;
    gap: 20px !important;
    margin-top: 12px !important;
}}
.yjre-stat {{
    text-align: center !important;
}}
.yjre-stat .lbl {{
    font-size: 10px !important;
    color: rgba(255,255,255,0.5) !important;
    margin-bottom: 2px !important;
    display: block !important;
}}
.yjre-stat .num {{
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #c084fc !important;
}}
.yjre-types {{
    display: flex !important;
    gap: 8px !important;
    margin-bottom: 12px !important;
}}
.yjre-type {{
    flex: 1 !important;
    background: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    padding: 10px 8px !important;
    text-align: center !important;
}}
.yjre-type .lbl {{
    font-size: 10px !important;
    color: #888 !important;
    margin-bottom: 2px !important;
    display: block !important;
}}
.yjre-type .num {{
    font-size: 16px !important;
    font-weight: 700 !important;
}}
.yjre-type .num.apt {{ color: #c084fc !important; }}
.yjre-type .num.villa {{ color: #60a5fa !important; }}
.yjre-type .num.house {{ color: #4ade80 !important; }}
.yjre-type .num.land {{ color: #fbbf24 !important; }}
.yjre-sec {{
    margin-bottom: 16px !important;
}}
.yjre-sec-title {{
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #fff !important;
    padding: 8px 0 !important;
    border-bottom: 1px solid #333 !important;
    margin-bottom: 8px !important;
}}
.yjre-sec-title span {{
    font-weight: 400 !important;
    color: #666 !important;
}}
.yjre-list {{
    display: flex !important;
    flex-direction: column !important;
    gap: 6px !important;
}}
.yjre-row {{
    background: #1a1a1a !important;
    border: 1px solid #282828 !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
}}
.yjre-row:hover {{ border-color: #444 !important; }}
.yjre-left {{ flex: 1 !important; min-width: 0 !important; }}
.yjre-name {{
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #fff !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    margin-bottom: 2px !important;
}}
.yjre-meta {{
    font-size: 11px !important;
    color: #777 !important;
}}
.yjre-meta span {{ margin-right: 6px !important; }}
.yjre-right {{ text-align: right !important; }}
.yjre-price {{
    font-size: 15px !important;
    font-weight: 700 !important;
}}
.yjre-price.apt {{ color: #c084fc !important; }}
.yjre-price.villa {{ color: #60a5fa !important; }}
.yjre-price.house {{ color: #4ade80 !important; }}
.yjre-price.land {{ color: #fbbf24 !important; }}
.yjre-empty {{
    text-align: center !important;
    padding: 16px !important;
    color: #555 !important;
    font-size: 12px !important;
}}
.yjre-footer {{
    text-align: center !important;
    padding: 12px 0 0 0 !important;
    font-size: 11px !important;
    color: #555 !important;
}}
.yjre-footer a {{ color: #c084fc !important; text-decoration: none !important; }}
@media (max-width: 500px) {{
    .yjre-types {{ flex-wrap: wrap !important; }}
    .yjre-type {{ flex: 1 1 45% !important; }}
    .yjre-row {{ flex-direction: column !important; align-items: flex-start !important; gap: 6px !important; }}
    .yjre-right {{ width: 100% !important; text-align: left !important; }}
}}
</style>

<div class="yjre-head">
    <h2>🏠 여주시 부동산 실거래가</h2>
    <p>{year}년 {month}월 · 국토교통부</p>
    <div class="yjre-stats">
        <div class="yjre-stat">
            <span class="lbl">총 거래</span>
            <span class="num">{total}건</span>
        </div>
        <div class="yjre-stat">
            <span class="lbl">평균가</span>
            <span class="num">{format_price(avg_price)}</span>
        </div>
        <div class="yjre-stat">
            <span class="lbl">최고가</span>
            <span class="num">{format_price(max_price)}</span>
        </div>
    </div>
</div>

<div class="yjre-types">
    <div class="yjre-type">
        <span class="lbl">아파트</span>
        <span class="num apt">{len(apt_trades)}</span>
    </div>
    <div class="yjre-type">
        <span class="lbl">연립/다세대</span>
        <span class="num villa">{len(villa_trades)}</span>
    </div>
    <div class="yjre-type">
        <span class="lbl">단독/다가구</span>
        <span class="num house">{len(house_trades)}</span>
    </div>
    <div class="yjre-type">
        <span class="lbl">토지</span>
        <span class="num land">{len(land_trades)}</span>
    </div>
</div>
'''

    if apt_trades:
        html += generate_section('아파트', 'apt', apt_trades)
    
    if villa_trades:
        html += generate_section('연립/다세대', 'villa', villa_trades)
    else:
        html += '<div class="yjre-sec"><div class="yjre-sec-title">연립/다세대 <span>(0건)</span></div><div class="yjre-empty">이번 달 거래 내역이 없습니다</div></div>'
    
    if house_trades:
        html += generate_section('단독/다가구', 'house', house_trades)
    else:
        html += '<div class="yjre-sec"><div class="yjre-sec-title">단독/다가구 <span>(0건)</span></div><div class="yjre-empty">이번 달 거래 내역이 없습니다</div></div>'
    
    if land_trades:
        html += generate_section('토지', 'land', land_trades)
    else:
        html += '<div class="yjre-sec"><div class="yjre-sec-title">토지 <span>(0건)</span></div><div class="yjre-empty">이번 달 거래 내역이 없습니다</div></div>'
    
    html += f'''
<div class="yjre-footer">
    자료: <a href="https://rt.molit.go.kr" target="_blank">국토교통부 실거래가 공개시스템</a> · 업데이트: {today}
</div>
</div>
'''
    return html


def generate_section(title: str, ptype: str, trades: List[Dict]) -> str:
    sorted_trades = sorted(trades, key=lambda x: (
        int(x['deal_year'] or 0),
        int(x['deal_month'] or 0),
        int(x['deal_day'] or 0)
    ), reverse=True)[:15]
    
    html = f'''
<div class="yjre-sec">
    <div class="yjre-sec-title">{title} <span>({len(trades)}건)</span></div>
    <div class="yjre-list">
'''
    
    for t in sorted_trades:
        amount = parse_amount(t['deal_amount'])
        area = float(t['area']) if t['area'] else 0
        pyeong = round(area / 3.3058, 1) if area else 0
        floor = t['floor'] if t['floor'] else ''
        floor_str = f"{floor}층" if floor else ""
        date_str = f"{t['deal_month']}/{t['deal_day']}"
        
        if ptype == 'land':
            meta = f"<span>{t['dong']}</span><span>{area}㎡</span><span>{date_str}</span>"
        else:
            meta = f"<span>{t['dong']}</span><span>{area}㎡({pyeong}평)</span>"
            if floor_str:
                meta += f"<span>{floor_str}</span>"
            meta += f"<span>{date_str}</span>"
        
        html += f'''
        <div class="yjre-row">
            <div class="yjre-left">
                <div class="yjre-name">{t['name']}</div>
                <div class="yjre-meta">{meta}</div>
            </div>
            <div class="yjre-right">
                <div class="yjre-price {ptype}">{format_price(amount)}</div>
            </div>
        </div>
'''
    
    html += '</div></div>'
    return html


def post_to_wordpress(title: str, content: str, category_id: int = None) -> bool:
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        output_file = f"realestate_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title></head><body style='background:#000;padding:20px;'>{content}</body></html>")
        print(f"✅ HTML 저장: {output_file}")
        return False
    
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    post_data = {'title': title, 'content': content, 'status': 'publish'}
    if category_id:
        post_data['categories'] = [category_id]
    
    try:
        response = requests.post(endpoint, json=post_data, auth=(WP_USER, WP_APP_PASSWORD), timeout=30)
        response.raise_for_status()
        print(f"✅ 발행: {response.json().get('link', '')}")
        return True
    except Exception as e:
        print(f"WP Error: {e}")
        return False


def main():
    print("🏠 여주 부동산 실거래가 업데이트...")
    
    current = datetime.now().strftime('%Y%m')
    last = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m')
    
    all_trades = []
    
    for ptype in ['apt', 'villa', 'house', 'land']:
        trades = fetch_trades(ptype, current)
        if len(trades) < 3:
            trades += fetch_trades(ptype, last)
        label = {'apt': '아파트', 'villa': '연립/다세대', 'house': '단독/다가구', 'land': '토지'}[ptype]
        print(f"  {label}: {len(trades)}건")
        all_trades.extend(trades)
    
    print(f"📊 총 {len(all_trades)}건")
    
    if not all_trades:
        print("데이터 없음")
        return
    
    content = generate_html(all_trades, current)
    year, month = current[:4], current[4:]
    title = f"[부동산] {year}년 {month}월 여주시 실거래가 ({len(all_trades)}건)"
    
    post_to_wordpress(title, content, category_id=137)
    print("✅ 완료!")


if __name__ == '__main__':
    main()
