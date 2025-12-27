#!/usr/bin/env python3
"""
여주굿뉴스 부동산 실거래가 자동화 스크립트 (최종본)
- 국토교통부 실거래가 API (아파트/연립다세대/단독다가구/토지)
- 탭 + 드롭다운 HTML 생성
- SNS 섬네일 이미지 생성
- 워드프레스 발행
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import json
import base64

# ============ 설정 ============
MOLIT_API_KEY = os.environ.get('MOLIT_API_KEY', '')
WP_URL = os.environ.get('WP_URL', 'https://yeojugoodnews.com')
WP_USER = os.environ.get('WP_USER', '')
WP_APP_PASSWORD = os.environ.get('WP_APP_PASSWORD', '')

YEOJU_CODE = '41670'

API_URLS = {
    'apt': 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade',
    'villa': 'https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade',
    'house': 'https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade',
    'land': 'https://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade',
}

TYPE_LABELS = {
    'apt': '아파트',
    'villa': '연립/다세대', 
    'house': '단독/다가구',
    'land': '토지'
}

TYPE_COLORS = {
    'apt': '#c084fc',
    'villa': '#60a5fa',
    'house': '#4ade80',
    'land': '#fbbf24'
}


# ============ API 호출 ============
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
                    'area': get_text(item, 'excluUseAr') or get_text(item, 'totFlrAr') or '',
                    'floor': get_text(item, 'floor'),
                    'deal_type': get_text(item, 'dealingGbn'),
                }
                if not trade['name']:
                    trade['name'] = f"{trade['dong']} {trade['jibun']}"
            trades.append(trade)
        
        return trades
        
    except Exception as e:
        print(f"  API Error ({property_type}): {e}")
        return []


def get_text(element, tag: str) -> str:
    el = element.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ''


# ============ 유틸리티 ============
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
            return f"{억}억 {만:,}만원"
        return f"{억}억원"
    return f"{amount:,}만원"


def format_price_short(amount: int) -> str:
    if amount >= 10000:
        억 = amount // 10000
        만 = amount % 10000
        if 만 > 0:
            return f"{억}억 {만:,}"
        return f"{억}억"
    return f"{amount:,}"


def get_week_of_month():
    now = datetime.now()
    first_day = now.replace(day=1)
    adjusted_dom = now.day + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1


# ============ HTML 생성 ============
def generate_html(data: Dict) -> str:
    now = datetime.now()
    year = now.year
    month = now.month
    week = get_week_of_month()
    week_names = ['첫째', '둘째', '셋째', '넷째', '다섯째']
    week_str = week_names[min(week-1, 4)]
    update_time = now.strftime('%Y-%m-%d %H:%M')
    
    # JSON 데이터 생성
    json_data = {
        'period': f"{year}년 {month}월 {week_str}주",
        'updateTime': update_time,
    }
    
    for ptype in ['apt', 'villa', 'house', 'land']:
        trades = data.get(ptype, [])
        amounts = [parse_amount(t['deal_amount']) for t in trades if parse_amount(t['deal_amount']) > 0]
        
        # 최신순 정렬
        sorted_trades = sorted(trades, key=lambda x: (
            int(x['deal_year'] or 0),
            int(x['deal_month'] or 0),
            int(x['deal_day'] or 0)
        ), reverse=True)[:20]
        
        # 최근 3일 내 거래 체크
        items = []
        for t in sorted_trades:
            try:
                deal_date = datetime(int(t['deal_year']), int(t['deal_month']), int(t['deal_day']))
                is_new = (now - deal_date).days <= 3
            except:
                is_new = False
            
            items.append({
                'name': t['name'],
                'dong': t['dong'],
                'area': float(t['area']) if t['area'] else 0,
                'floor': int(t['floor']) if t['floor'] else 0,
                'price': parse_amount(t['deal_amount']),
                'buildYear': int(t['build_year']) if t['build_year'] else 0,
                'dealDate': f"{t['deal_month']}/{t['deal_day']}",
                'dealType': t['deal_type'] or '중개거래',
                'isNew': is_new
            })
        
        json_data[ptype] = {
            'total': len(trades),
            'avg': format_price_short(int(sum(amounts) / len(amounts))) if amounts else '-',
            'max': format_price_short(max(amounts)) if amounts else '-',
            'items': items
        }
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>여주시 부동산 실거래가</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #1a1a1a; }}
        ::-webkit-scrollbar-thumb {{ background: #444; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #555; }}
        html {{ scrollbar-width: thin; scrollbar-color: #444 #1a1a1a; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
            background: #0a0a0a;
            color: #e5e5e5;
            line-height: 1.5;
            padding: 12px;
        }}
        .tabs {{
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
        }}
        .tab {{
            flex: 1;
            padding: 10px 6px;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #888;
            font-size: 11px;
            font-weight: 600;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab:hover {{ border-color: #555; }}
        .tab.active {{
            background: linear-gradient(135deg, #4a1d6a, #2d1245);
            border-color: #6b3d99;
            color: #fff;
        }}
        .tab .count {{
            display: block;
            font-size: 18px;
            font-weight: 700;
            margin-top: 2px;
        }}
        .tab[data-type="apt"] .count {{ color: #c084fc; }}
        .tab[data-type="villa"] .count {{ color: #60a5fa; }}
        .tab[data-type="house"] .count {{ color: #4ade80; }}
        .tab[data-type="land"] .count {{ color: #fbbf24; }}
        .header {{
            background: linear-gradient(135deg, #4a1d6a, #1a0a2e);
            border: 1px solid #6b3d99;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .header.villa {{ background: linear-gradient(135deg, #1e3a5f, #0f1f33); border-color: #3b82f6; }}
        .header.house {{ background: linear-gradient(135deg, #14532d, #0a2615); border-color: #22c55e; }}
        .header.land {{ background: linear-gradient(135deg, #713f12, #3d2106); border-color: #f59e0b; }}
        .header h1 {{ font-size: 16px; margin-bottom: 2px; }}
        .header .subtitle {{ font-size: 11px; color: rgba(255,255,255,0.5); margin-bottom: 12px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }}
        .stat {{
            text-align: center;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            padding: 8px 4px;
        }}
        .stat .label {{ font-size: 10px; color: rgba(255,255,255,0.5); }}
        .stat .value {{ font-size: 14px; font-weight: 700; color: #c084fc; }}
        .header.villa .stat .value {{ color: #60a5fa; }}
        .header.house .stat .value {{ color: #4ade80; }}
        .header.land .stat .value {{ color: #fbbf24; }}
        .list {{ display: flex; flex-direction: column; gap: 6px; }}
        .card {{
            background: #141414;
            border: 1px solid #252525;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
        }}
        .card:hover {{ border-color: #444; }}
        .card-main {{
            padding: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .card-left {{ flex: 1; min-width: 0; }}
        .card-name {{
            font-size: 13px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 3px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .card-name span {{
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .badge {{
            background: rgba(74, 222, 128, 0.15);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.3);
            font-size: 9px;
            padding: 1px 5px;
            border-radius: 4px;
            flex-shrink: 0;
        }}
        .card-meta {{
            font-size: 11px;
            color: #666;
        }}
        .card-meta span {{ margin-right: 6px; }}
        .card-right {{
            text-align: right;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .card-price {{ font-size: 14px; font-weight: 700; }}
        .card-price.apt {{ color: #c084fc; }}
        .card-price.villa {{ color: #60a5fa; }}
        .card-price.house {{ color: #4ade80; }}
        .card-price.land {{ color: #fbbf24; }}
        .arrow {{
            width: 18px;
            height: 18px;
            color: #555;
            transition: transform 0.3s;
        }}
        .card.open .arrow {{ transform: rotate(180deg); }}
        .card-detail {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: #0f0f0f;
        }}
        .card.open .card-detail {{ max-height: 250px; }}
        .card-detail-inner {{
            padding: 12px;
            border-top: 1px solid #222;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}
        .detail-item {{ display: flex; flex-direction: column; gap: 1px; }}
        .detail-item .label {{ font-size: 10px; color: #555; }}
        .detail-item .value {{ font-size: 12px; color: #aaa; }}
        .footer {{
            text-align: center;
            padding: 16px 0 8px;
            font-size: 10px;
            color: #444;
        }}
        .footer a {{ color: #c084fc; text-decoration: none; }}
        .empty {{
            text-align: center;
            padding: 30px 20px;
            color: #555;
            font-size: 12px;
        }}
        .content {{ display: none; }}
        .content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="tabs">
        <div class="tab active" data-type="apt" onclick="switchTab('apt')">
            아파트<span class="count" id="apt-count">0</span>
        </div>
        <div class="tab" data-type="villa" onclick="switchTab('villa')">
            연립/다세대<span class="count" id="villa-count">0</span>
        </div>
        <div class="tab" data-type="house" onclick="switchTab('house')">
            단독/다가구<span class="count" id="house-count">0</span>
        </div>
        <div class="tab" data-type="land" onclick="switchTab('land')">
            토지<span class="count" id="land-count">0</span>
        </div>
    </div>
    
    <div id="content-apt" class="content active">
        <div class="header">
            <h1>🏢 여주시 아파트 실거래가</h1>
            <p class="subtitle" id="apt-period"></p>
            <div class="stats">
                <div class="stat"><div class="label">거래건수</div><div class="value" id="apt-total">0건</div></div>
                <div class="stat"><div class="label">평균가</div><div class="value" id="apt-avg">-</div></div>
                <div class="stat"><div class="label">최고가</div><div class="value" id="apt-max">-</div></div>
            </div>
        </div>
        <div class="list" id="apt-list"></div>
    </div>
    
    <div id="content-villa" class="content">
        <div class="header villa">
            <h1>🏘️ 여주시 연립/다세대 실거래가</h1>
            <p class="subtitle" id="villa-period"></p>
            <div class="stats">
                <div class="stat"><div class="label">거래건수</div><div class="value" id="villa-total">0건</div></div>
                <div class="stat"><div class="label">평균가</div><div class="value" id="villa-avg">-</div></div>
                <div class="stat"><div class="label">최고가</div><div class="value" id="villa-max">-</div></div>
            </div>
        </div>
        <div class="list" id="villa-list"></div>
    </div>
    
    <div id="content-house" class="content">
        <div class="header house">
            <h1>🏠 여주시 단독/다가구 실거래가</h1>
            <p class="subtitle" id="house-period"></p>
            <div class="stats">
                <div class="stat"><div class="label">거래건수</div><div class="value" id="house-total">0건</div></div>
                <div class="stat"><div class="label">평균가</div><div class="value" id="house-avg">-</div></div>
                <div class="stat"><div class="label">최고가</div><div class="value" id="house-max">-</div></div>
            </div>
        </div>
        <div class="list" id="house-list"></div>
    </div>
    
    <div id="content-land" class="content">
        <div class="header land">
            <h1>🌳 여주시 토지 실거래가</h1>
            <p class="subtitle" id="land-period"></p>
            <div class="stats">
                <div class="stat"><div class="label">거래건수</div><div class="value" id="land-total">0건</div></div>
                <div class="stat"><div class="label">평균가</div><div class="value" id="land-avg">-</div></div>
                <div class="stat"><div class="label">최고가</div><div class="value" id="land-max">-</div></div>
            </div>
        </div>
        <div class="list" id="land-list"></div>
    </div>
    
    <div class="footer">
        자료: <a href="https://rt.molit.go.kr" target="_blank">국토교통부 실거래가 공개시스템</a><br>
        <span id="update-time"></span>
    </div>

    <script>
        const DATA = {json.dumps(json_data, ensure_ascii=False)};
        
        function formatPrice(amount) {{
            if (amount >= 10000) {{
                const 억 = Math.floor(amount / 10000);
                const 만 = amount % 10000;
                return 만 > 0 ? `${{억}}억 ${{만.toLocaleString()}}만원` : `${{억}}억원`;
            }}
            return `${{amount.toLocaleString()}}만원`;
        }}
        
        function toPyeong(area) {{ return (area / 3.3058).toFixed(1); }}
        
        function switchTab(type) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab[data-type="${{type}}"]`).classList.add('active');
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.getElementById(`content-${{type}}`).classList.add('active');
        }}
        
        function toggleCard(card) {{
            const wasOpen = card.classList.contains('open');
            document.querySelectorAll('.card.open').forEach(c => c.classList.remove('open'));
            if (!wasOpen) {{
                card.classList.add('open');
                setTimeout(() => card.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }}), 100);
            }}
        }}
        
        function createCard(item, type) {{
            const pyeong = toPyeong(item.area);
            const priceText = formatPrice(item.price);
            const badge = item.isNew ? '<span class="badge">NEW</span>' : '';
            const floor = item.floor ? `${{item.floor}}층` : '';
            
            return `
                <div class="card" onclick="toggleCard(this)">
                    <div class="card-main">
                        <div class="card-left">
                            <div class="card-name"><span>${{item.name}}</span>${{badge}}</div>
                            <div class="card-meta">
                                <span>${{item.dong}}</span>
                                <span>${{item.area}}㎡(${{pyeong}}평)</span>
                                ${{floor ? `<span>${{floor}}</span>` : ''}}
                                <span>${{item.dealDate}}</span>
                            </div>
                        </div>
                        <div class="card-right">
                            <div class="card-price ${{type}}">${{priceText}}</div>
                            <svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 9l-7 7-7-7"/>
                            </svg>
                        </div>
                    </div>
                    <div class="card-detail">
                        <div class="card-detail-inner">
                            <div class="detail-item"><span class="label">전용면적</span><span class="value">${{item.area}}㎡ (${{pyeong}}평)</span></div>
                            <div class="detail-item"><span class="label">거래금액</span><span class="value">${{priceText}}</span></div>
                            ${{item.floor ? `<div class="detail-item"><span class="label">층수</span><span class="value">${{item.floor}}층</span></div>` : ''}}
                            ${{item.buildYear ? `<div class="detail-item"><span class="label">건축년도</span><span class="value">${{item.buildYear}}년</span></div>` : ''}}
                            <div class="detail-item"><span class="label">계약일</span><span class="value">2025.${{item.dealDate}}</span></div>
                            <div class="detail-item"><span class="label">거래유형</span><span class="value">${{item.dealType}}</span></div>
                        </div>
                    </div>
                </div>
            `;
        }}
        
        function init() {{
            ['apt', 'villa', 'house', 'land'].forEach(type => {{
                const d = DATA[type];
                document.getElementById(`${{type}}-count`).textContent = d.total;
                document.getElementById(`${{type}}-total`).textContent = `${{d.total}}건`;
                document.getElementById(`${{type}}-avg`).textContent = d.avg;
                document.getElementById(`${{type}}-max`).textContent = d.max;
                document.getElementById(`${{type}}-period`).textContent = DATA.period + ' 기준 · 국토교통부';
                
                const list = document.getElementById(`${{type}}-list`);
                list.innerHTML = d.items.length === 0 
                    ? '<div class="empty">이번 달 거래 내역이 없습니다</div>'
                    : d.items.map(item => createCard(item, type)).join('');
            }});
            document.getElementById('update-time').textContent = '업데이트: ' + DATA.updateTime;
        }}
        
        init();
    </script>
</body>
</html>'''
    
    return html


# ============ 섬네일 생성 ============
def create_thumbnail(apt_count, villa_count, house_count, land_count, output_path="thumbnail.png"):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow 없음 - 섬네일 생략")
        return None
    
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), '#0f0f1a')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경
    for y in range(height):
        r = int(15 + (y / height) * 15)
        g = int(15 + (y / height) * 8)
        b = int(26 + (y / height) * 25)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    draw.ellipse([(-150, -150), (250, 250)], fill='#2d1f4e')
    draw.ellipse([(950, 450), (1350, 850)], fill='#1a1a3e')
    
    # 폰트
    try:
        font_bold_lg = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 64)
        font_bold_md = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 44)
        font_count = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 48)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf", 22)
    except:
        print("  폰트 없음 - 섬네일 생략")
        return None
    
    now = datetime.now()
    month = now.month
    
    # 집 아이콘
    ix, iy = 100, 120
    draw.polygon([(ix, iy+30), (ix+40, iy), (ix+80, iy+30)], fill='#c084fc')
    draw.rectangle([ix+10, iy+30, ix+70, iy+70], fill='#c084fc')
    draw.rectangle([ix+30, iy+45, ix+50, iy+70], fill='#1a1a2e')
    
    draw.text((width//2 + 30, 135), "여주시 부동산 실거래", font=font_bold_lg, fill='#ffffff', anchor='mm')
    draw.text((width//2, 210), f"{month}월 전체 거래 현황", font=font_bold_md, fill='#c084fc', anchor='mm')
    draw.line([(200, 260), (1000, 260)], fill='#333355', width=1)
    
    box_y, box_h, box_w, gap = 310, 160, 220, 35
    start_x = (width - (box_w * 4 + gap * 3)) // 2
    
    categories = [
        ("아파트", apt_count, "#c084fc", "#3d2066"),
        ("연립/다세대", villa_count, "#60a5fa", "#1e3a5f"),
        ("단독/다가구", house_count, "#4ade80", "#14532d"),
        ("토지", land_count, "#fbbf24", "#713f12"),
    ]
    
    for i, (label, count, color, bg) in enumerate(categories):
        x = start_x + i * (box_w + gap)
        draw.rounded_rectangle([x, box_y, x+box_w, box_y+box_h], radius=16, fill=bg, outline=color, width=2)
        draw.text((x + box_w//2, box_y + 45), label, font=font_label, fill='#aaaaaa', anchor='mm')
        draw.text((x + box_w//2, box_y + 105), f"{count}건", font=font_count, fill=color, anchor='mm')
    
    draw.text((width//2, 550), "여주소식", font=font_bold_md, fill='#555555', anchor='mm')
    draw.text((width//2, 595), "yjgood.kr", font=font_label, fill='#444444', anchor='mm')
    
    img.save(output_path, 'PNG', quality=95)
    print(f"  ✅ 섬네일: {output_path}")
    return output_path


# ============ 워드프레스 발행 ============
def upload_media(file_path: str) -> str:
    """워드프레스에 이미지 업로드"""
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        return None
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        filename = os.path.basename(file_path)
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'image/png'
            },
            data=file_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get('id'), result.get('source_url')
    except Exception as e:
        print(f"  미디어 업로드 실패: {e}")
        return None, None


def post_to_wordpress(title: str, content: str, category_id: int = None, thumbnail_id: int = None) -> bool:
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        with open("realestate_output.html", 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ HTML 파일 저장: realestate_output.html")
        return False
    
    post_data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    if category_id:
        post_data['categories'] = [category_id]
    if thumbnail_id:
        post_data['featured_media'] = thumbnail_id
    
    try:
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=post_data,
            auth=(WP_USER, WP_APP_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"  ✅ 발행: {result.get('link', '')}")
        return True
    except Exception as e:
        print(f"  발행 실패: {e}")
        return False


# ============ 메인 ============
def main():
    print("🏠 여주 부동산 실거래가 업데이트 시작...")
    
    current = datetime.now().strftime('%Y%m')
    last = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m')
    
    data = {}
    counts = {}
    
    for ptype in ['apt', 'villa', 'house', 'land']:
        trades = fetch_trades(ptype, current)
        if len(trades) < 3:
            trades += fetch_trades(ptype, last)
        
        data[ptype] = trades
        counts[ptype] = len(trades)
        print(f"  {TYPE_LABELS[ptype]}: {len(trades)}건")
    
    total = sum(counts.values())
    print(f"📊 총 {total}건")
    
    if total == 0:
        print("거래 데이터 없음")
        return
    
    # HTML 생성
    html_content = generate_html(data)
    
    # HTML 파일 저장 (GitHub Pages용)
    with open("index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("  ✅ index.html 생성")
    
    # 섬네일 생성
    thumb_path = create_thumbnail(counts['apt'], counts['villa'], counts['house'], counts['land'], "thumbnail.png")
    
    # 워드프레스 발행
    now = datetime.now()
    week = get_week_of_month()
    week_names = ['첫째', '둘째', '셋째', '넷째', '다섯째']
    week_str = week_names[min(week-1, 4)]
    
    title = f"{now.month}월 {week_str}주 여주시 부동산 실거래가 ({total}건)"
    
    # iframe으로 GitHub Pages 삽입
    iframe_content = f'''
<iframe src="https://leekkyg.github.io/realestate-bot/" width="100%" height="800" style="border:none; border-radius:12px; max-width:600px;" loading="lazy"></iframe>

<p style="font-size:12px; color:#666; margin-top:16px;">※ {now.month}월 {week_str}주 기준 업데이트 · 거래건수는 {now.month}월 전체 누적<br>자료 출처: 국토교통부 실거래가 공개시스템</p>
'''
    
    # 섬네일 업로드
    thumb_id = None
    if thumb_path and os.path.exists(thumb_path):
        thumb_id, thumb_url = upload_media(thumb_path)
        if thumb_id:
            print(f"  ✅ 섬네일 업로드: {thumb_url}")
    
    post_to_wordpress(title, iframe_content, category_id=137, thumbnail_id=thumb_id)
    
    print("✅ 완료!")


if __name__ == '__main__':
    main()
