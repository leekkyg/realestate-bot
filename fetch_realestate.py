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
        
        # XML 파싱
        root = ET.fromstring(response.content)
        
        # 에러 체크
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
    """XML 요소에서 텍스트 추출"""
    el = element.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ''


def parse_deal_amount(amount_str: str) -> int:
    """거래금액 파싱 (만원 단위)"""
    try:
        return int(amount_str.replace(',', '').strip())
    except:
        return 0


def format_price(amount: int) -> str:
    """가격 포맷팅"""
    if amount >= 10000:
        억 = amount // 10000
        만 = amount % 10000
        if 만 > 0:
            return f"{억}억 {만:,}"
        return f"{억}억"
    return f"{amount:,}"


def calculate_price_per_area(amount: int, area: float) -> int:
    """평당 가격 계산 (만원)"""
    if area <= 0:
        return 0
    pyeong = area / 3.3058
    return int(amount / pyeong)


def generate_html(trades: List[Dict], year_month: str) -> str:
    """부동산 실거래가 HTML 생성"""
    year = year_month[:4]
    month = year_month[4:]
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 통계 계산
    total_count = len(trades)
    amounts = [parse_deal_amount(t['deal_amount']) for t in trades if parse_deal_amount(t['deal_amount']) > 0]
    avg_price = int(sum(amounts) / len(amounts)) if amounts else 0
    max_price = max(amounts) if amounts else 0
    
    # 최근 7일 거래 (신규)
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
    
    # 아파트별 거래 수
    apt_counts = defaultdict(int)
    for t in trades:
        if t['apt_name']:
            apt_counts[t['apt_name']] += 1
    top_apt = max(apt_counts.items(), key=lambda x: x[1]) if apt_counts else ('', 0)
    top_apt_name = top_apt[0][:12] + '...' if len(top_apt[0]) > 12 else top_apt[0]
    
    html = f'''
<style>
.yj-re-container {{
    font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
    background: #0f0f0f;
    color: #e5e5e5;
    line-height: 1.6;
    padding: 20px;
    border-radius: 16px;
}}
.yj-re-header {{
    background: linear-gradient(135deg, #4a1d6a 0%, #1a0a2e 100%);
    border: 1px solid #6b3d99;
    color: white;
    padding: 30px;
    border-radius: 16px;
    margin-bottom: 24px;
}}
.yj-re-header h2 {{
    font-size: 28px;
    margin: 0 0 8px 0;
}}
.yj-re-header .subtitle {{
    opacity: 0.7;
    font-size: 15px;
}}
.yj-re-header .stats {{
    display: flex;
    gap: 24px;
    margin-top: 20px;
    flex-wrap: wrap;
}}
.yj-re-header .stat-item {{
    text-align: center;
}}
.yj-re-header .stat-number {{
    font-size: 28px;
    font-weight: 700;
    color: #c084fc;
}}
.yj-re-header .stat-label {{
    font-size: 13px;
    opacity: 0.7;
}}
.yj-summary-cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}}
.yj-summary-card {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px;
}}
.yj-summary-card .label {{
    font-size: 13px;
    color: #666;
    margin-bottom: 8px;
}}
.yj-summary-card .value {{
    font-size: 22px;
    font-weight: 700;
    color: #fff;
}}
.yj-summary-card .sub {{
    font-size: 13px;
    color: #888;
    margin-top: 4px;
}}
.yj-section-title {{
    font-size: 18px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.yj-section-title .count {{
    background: #333;
    color: #999;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 400;
}}
.yj-tap-hint {{
    text-align: center;
    padding: 12px;
    color: #444;
    font-size: 13px;
    margin-bottom: 16px;
}}
.yj-re-list {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 32px;
}}
.yj-re-card {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    overflow: hidden;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    user-select: none;
    transition: all 0.2s;
}}
.yj-re-card:active {{
    background: #222;
}}
.yj-re-card-main {{
    padding: 20px;
    position: relative;
}}
.yj-re-expand-icon {{
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    height: 24px;
    color: #555;
    transition: transform 0.3s;
}}
.yj-re-card.expanded .yj-re-expand-icon {{
    transform: translateY(-50%) rotate(180deg);
}}
.yj-re-header-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
    padding-right: 30px;
}}
.yj-re-name {{
    font-size: 17px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 4px;
}}
.yj-re-address {{
    font-size: 14px;
    color: #888;
}}
.yj-re-price {{
    text-align: right;
}}
.yj-re-price .amount {{
    font-size: 20px;
    font-weight: 700;
    color: #c084fc;
}}
.yj-re-price .per-area {{
    font-size: 12px;
    color: #666;
    margin-top: 2px;
}}
.yj-re-summary {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 14px;
    color: #aaa;
}}
.yj-re-badge {{
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}}
.yj-re-badge.new {{
    background: rgba(74, 222, 128, 0.15);
    color: #4ade80;
    border: 1px solid rgba(74, 222, 128, 0.3);
}}
.yj-re-badge.high {{
    background: rgba(248, 113, 113, 0.15);
    color: #f87171;
    border: 1px solid rgba(248, 113, 113, 0.3);
}}
.yj-re-detail {{
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease-out;
    background: #151515;
}}
.yj-re-card.expanded .yj-re-detail {{
    max-height: 350px;
}}
.yj-re-detail-inner {{
    padding: 20px;
    border-top: 1px solid #252525;
}}
.yj-re-detail-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}}
.yj-re-detail-item {{
    display: flex;
    flex-direction: column;
    gap: 4px;
}}
.yj-re-detail-item .label {{
    font-size: 12px;
    color: #666;
}}
.yj-re-detail-item .value {{
    font-size: 15px;
    color: #ccc;
}}
.yj-re-footer {{
    text-align: center;
    padding: 24px;
    color: #555;
    font-size: 13px;
}}
.yj-re-footer a {{
    color: #c084fc;
    text-decoration: none;
}}
@media (max-width: 600px) {{
    .yj-re-header {{
        padding: 20px;
    }}
    .yj-re-header h2 {{
        font-size: 22px;
    }}
    .yj-re-header .stats {{
        gap: 16px;
    }}
    .yj-re-header .stat-number {{
        font-size: 22px;
    }}
    .yj-re-header-row {{
        flex-direction: column;
        gap: 12px;
    }}
    .yj-re-price {{
        text-align: left;
    }}
    .yj-re-detail-grid {{
        grid-template-columns: 1fr;
    }}
    .yj-summary-cards {{
        grid-template-columns: 1fr 1fr;
    }}
}}
</style>

<div class="yj-re-container">
    <div class="yj-re-header">
        <h2>🏠 여주시 부동산 실거래가</h2>
        <p class="subtitle">{year}년 {month}월 기준 · 국토교통부 실거래가 공개시스템</p>
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{total_count}</div>
                <div class="stat-label">{month}월 거래건수</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{format_price(avg_price)}</div>
                <div class="stat-label">평균 거래가</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(recent_trades)}</div>
                <div class="stat-label">최근 7일</div>
            </div>
        </div>
    </div>

    <div class="yj-summary-cards">
        <div class="yj-summary-card">
            <div class="label">최고가 거래</div>
            <div class="value">{format_price(max_price)}</div>
        </div>
        <div class="yj-summary-card">
            <div class="label">최다 거래 단지</div>
            <div class="value">{top_apt[1]}건</div>
            <div class="sub">{top_apt_name}</div>
        </div>
    </div>

    <div class="yj-section-title">
        최근 거래 내역 <span class="count">아파트 {total_count}건</span>
    </div>

    <p class="yj-tap-hint">거래 내역을 탭하면 상세정보를 볼 수 있습니다</p>

    <div class="yj-re-list">
'''

    # 거래 내역을 최신순으로 정렬
    sorted_trades = sorted(trades, key=lambda x: (
        int(x['deal_year'] or 0),
        int(x['deal_month'] or 0),
        int(x['deal_day'] or 0)
    ), reverse=True)

    for trade in sorted_trades[:30]:  # 최근 30건만
        amount = parse_deal_amount(trade['deal_amount'])
        area = float(trade['exclusive_area'] or 0)
        pyeong = round(area / 3.3058, 1)
        price_per_pyeong = calculate_price_per_area(amount, area)
        
        # 뱃지
        badge_html = ''
        try:
            deal_day = int(trade['deal_day']) if trade['deal_day'] else 0
            deal_month = int(trade['deal_month']) if trade['deal_month'] else 0
            deal_year = int(trade['deal_year']) if trade['deal_year'] else 0
            if deal_day and deal_month and deal_year:
                deal_datetime = datetime(deal_year, deal_month, deal_day)
                if (datetime.now() - deal_datetime).days <= 3:
                    badge_html = '<span class="yj-re-badge new">NEW</span>'
        except:
            pass
        
        floor_str = trade['floor'] if trade['floor'] else '-'
        deal_month_str = trade['deal_month'] if trade['deal_month'] else ''
        deal_day_str = trade['deal_day'] if trade['deal_day'] else ''
        
        html += f'''
        <div class="yj-re-card" onclick="toggleReCard(this)">
            <div class="yj-re-card-main">
                <svg class="yj-re-expand-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
                <div class="yj-re-header-row">
                    <div>
                        <div class="yj-re-name">
                            {trade['apt_name']}
                            {badge_html}
                        </div>
                        <div class="yj-re-address">여주시 {trade['dong']} {trade['jibun']}</div>
                    </div>
                    <div class="yj-re-price">
                        <div class="amount">{format_price(amount)}</div>
                        <div class="per-area">평당 {price_per_pyeong:,}만</div>
                    </div>
                </div>
                <div class="yj-re-summary">
                    <span>{area}㎡ ({pyeong}평)</span>
                    <span>{floor_str}층</span>
                    <span>{deal_month_str}/{deal_day_str} 계약</span>
                </div>
            </div>
            <div class="yj-re-detail">
                <div class="yj-re-detail-inner">
                    <div class="yj-re-detail-grid">
                        <div class="yj-re-detail-item">
                            <span class="label">전용면적</span>
                            <span class="value">{area}㎡ ({pyeong}평)</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">거래금액</span>
                            <span class="value">{format_price(amount)}만원</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">층</span>
                            <span class="value">{floor_str}층</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">건축년도</span>
                            <span class="value">{trade['build_year']}년</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">계약일</span>
                            <span class="value">{trade['deal_year']}.{trade['deal_month']}.{trade['deal_day']}</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">거래유형</span>
                            <span class="value">{trade['deal_type'] or '중개거래'}</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">법정동</span>
                            <span class="value">{trade['dong']}</span>
                        </div>
                        <div class="yj-re-detail-item">
                            <span class="label">평당가</span>
                            <span class="value">{price_per_pyeong:,}만원</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
'''

    html += f'''
    </div>

    <div class="yj-re-footer">
        <p>자료 출처: <a href="https://rt.molit.go.kr" target="_blank">국토교통부 실거래가 공개시스템</a></p>
        <p style="margin-top: 8px; color: #444;">※ 실거래 신고 후 자료 반영까지 시차가 있을 수 있습니다</p>
        <p style="margin-top: 8px;">업데이트: {today}</p>
    </div>
</div>

<script>
var yjReTouchStartY = 0;
var yjReTouchEndY = 0;
var yjReIsTouchMove = false;

document.addEventListener('touchstart', function(e) {{
    yjReTouchStartY = e.touches[0].clientY;
    yjReIsTouchMove = false;
}}, {{ passive: true }});

document.addEventListener('touchmove', function(e) {{
    yjReTouchEndY = e.touches[0].clientY;
    if (Math.abs(yjReTouchStartY - yjReTouchEndY) > 10) {{
        yjReIsTouchMove = true;
    }}
}}, {{ passive: true }});

function toggleReCard(card) {{
    if (yjReIsTouchMove) return;
    
    var allCards = document.querySelectorAll('.yj-re-card.expanded');
    allCards.forEach(function(openCard) {{
        if (openCard !== card) {{
            openCard.classList.remove('expanded');
        }}
    }});
    
    card.classList.toggle('expanded');
    
    if (card.classList.contains('expanded')) {{
        setTimeout(function() {{
            var rect = card.getBoundingClientRect();
            var offsetTop = window.pageYOffset + rect.top - 100;
            window.scrollTo({{
                top: offsetTop,
                behavior: 'smooth'
            }});
        }}, 100);
    }}
}}
</script>
'''

    return html


def post_to_wordpress(title: str, content: str, category_id: int = None) -> bool:
    """워드프레스에 포스트 발행"""
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
    
    # 이번 달 조회
    current_month = datetime.now().strftime('%Y%m')
    
    # 아파트 매매 실거래가 조회
    trades = fetch_apt_trades(deal_ymd=current_month)
    
    # 이번 달 거래가 적으면 지난 달도 조회
    if len(trades) < 10:
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m')
        last_month_trades = fetch_apt_trades(deal_ymd=last_month)
        trades.extend(last_month_trades)
        print(f"📊 지난달 포함 총 {len(trades)}건")
    
    if not trades:
        print("거래 데이터가 없습니다.")
        return
    
    # HTML 생성
    content = generate_html(trades, current_month)
    
    # 제목 생성
    year = current_month[:4]
    month = current_month[4:]
    title = f"[부동산] {year}년 {month}월 여주시 아파트 실거래가 ({len(trades)}건)"
    
    # 워드프레스 발행
    post_to_wordpress(title, content, category_id=137)
    
    print("✅ 완료!")


if __name__ == '__main__':
    main()
