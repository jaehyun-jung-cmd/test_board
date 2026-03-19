"""
주식조회 뷰

- GET /stocks/         → 검색 UI 페이지
- GET /stocks/api/search/?q=삼성   → 종목 자동완성 (KR)
- GET /stocks/api/quote/?market=KR&code=005930  → 시세·차트·뉴스
- GET /stocks/api/quote/?market=US&code=AAPL    → yfinance 시세·차트·뉴스
"""
import requests
import yfinance as yf

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

# Naver Finance 엔드포인트
_NAVER_SEARCH = 'https://ac.stock.naver.com/ac'
_NAVER_BASIC  = 'https://m.stock.naver.com/api/stock/{code}/basic'
_NAVER_CHART  = 'https://api.stock.naver.com/chart/domestic/item/{code}/day'
_NAVER_NEWS   = 'https://finance.naver.com/item/news_news.naver'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0 Safari/537.36'
    ),
    'Referer': 'https://finance.naver.com/',
}


def index(request):
    """GET /stocks/ → 빈 검색 페이지 렌더링"""
    return render(request, 'stocks/index.html')


@require_GET
def api_search(request):
    """GET /stocks/api/search/?q=삼성 → KR 자동완성 JSON
    Returns: {"results": [{"code": "005930", "name": "삼성전자"}, ...]}
    """
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})

    resp = requests.get(
        _NAVER_SEARCH,
        params={'q': q, 'target': 'stock'},
        headers=_HEADERS,
        timeout=5,
    )

    results = []
    if resp.status_code == 200:
        data = resp.json()
        # items는 [{"code": "005930", "name": "삼성전자", ...}, ...]  구조
        for item in data.get('items', []):
            if isinstance(item, dict) and 'code' in item and 'name' in item:
                results.append({'code': item['code'], 'name': item['name']})

    return JsonResponse({'results': results})


@require_GET
def api_quote(request):
    """GET /stocks/api/quote/?market=KR&code=005930
    GET /stocks/api/quote/?market=US&code=AAPL
    Returns: {name, code, market, price, change, change_pct, currency,
              chart:{dates,prices}, news:[{title,url,source}]}
    """
    code   = request.GET.get('code', '').strip()
    market = request.GET.get('market', 'KR').upper()

    if not code:
        return JsonResponse({'error': 'code 파라미터가 필요합니다.'}, status=400)

    if market == 'US':
        return _fetch_us(code)
    else:
        return _fetch_kr(code)


def _fetch_kr(code):
    """Naver Finance API 3번 호출 (시세, 차트, 뉴스)"""
    # 1) 시세 (필수)
    basic_resp = requests.get(
        _NAVER_BASIC.format(code=code),
        headers=_HEADERS,
        timeout=5,
    )
    if basic_resp.status_code != 200:
        return JsonResponse({'error': f'종목 코드를 찾을 수 없습니다: {code}'}, status=404)

    basic = basic_resp.json()
    price      = basic.get('closePrice', '')
    change     = basic.get('compareToPreviousClosePrice', '')
    change_pct = basic.get('fluctuationsRatio', '')
    name       = basic.get('stockName', code)

    # 2) 차트 (비필수) - API는 날짜 범위 파라미터로 3개월치 조회
    chart = {'dates': [], 'prices': []}
    try:
        today = datetime.now()
        start = today - timedelta(days=90)
        chart_resp = requests.get(
            _NAVER_CHART.format(code=code),
            params={
                'startDateTime': start.strftime('%Y%m%d'),
                'endDateTime':   today.strftime('%Y%m%d'),
            },
            headers=_HEADERS,
            timeout=5,
        )
        if chart_resp.status_code == 200:
            items = chart_resp.json()  # 직접 리스트 반환
            if isinstance(items, list):
                chart = {
                    'dates':  [item['localDate'] for item in items],
                    'prices': [item['closePrice'] for item in items],
                }
    except Exception:
        pass

    # 3) 뉴스 (비필수) - 네이버 금융 HTML 스크래핑
    news = []
    try:
        news_resp = requests.get(
            _NAVER_NEWS,
            params={'code': code, 'page': '1'},
            headers=_HEADERS,
            timeout=5,
        )
        if news_resp.status_code == 200:
            html = news_resp.content.decode('euc-kr')
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', class_='type5')
            if table:
                for row in table.find_all('tr'):
                    a = row.find('a')
                    if not a:
                        continue
                    title = a.text.strip()
                    href = a.get('href', '')
                    td_source = row.find('td', class_='info')
                    source = td_source.text.strip() if td_source else ''
                    if title and href:
                        news.append({
                            'title':  title,
                            'url':    'https://finance.naver.com' + href,
                            'source': source,
                        })
                    if len(news) >= 10:
                        break
    except Exception:
        pass

    return JsonResponse({
        'name':       name,
        'code':       code,
        'market':     'KR',
        'price':      price,
        'change':     change,
        'change_pct': change_pct,
        'currency':   'KRW',
        'chart':      chart,
        'news':       news,
    })


def _fetch_us(code):
    """yfinance로 info, history, news 조회"""
    ticker = yf.Ticker(code)
    info   = ticker.info

    if not info or not info.get('currentPrice') and not info.get('regularMarketPrice'):
        return JsonResponse({'error': f'종목을 찾을 수 없습니다: {code}'}, status=404)

    price      = info.get('currentPrice') or info.get('regularMarketPrice')
    change     = info.get('regularMarketChange', 0)
    change_pct = info.get('regularMarketChangePercent', 0)
    name       = info.get('shortName', code)
    currency   = info.get('currency', 'USD')

    # 차트 (3개월 일봉)
    chart = {'dates': [], 'prices': []}
    try:
        hist = ticker.history(period='3mo')
        if not hist.empty:
            chart = {
                'dates':  [str(d.date()) for d in hist.index],
                'prices': [round(float(p), 2) for p in hist['Close']],
            }
    except Exception:
        pass

    # 뉴스 - yfinance 0.2.x 이후 구조: item['content'] 안에 데이터
    news = []
    try:
        for item in (ticker.news or [])[:10]:
            content = item.get('content', {})
            if content:
                title  = content.get('title', '')
                url    = (content.get('canonicalUrl') or {}).get('url', '') \
                      or (content.get('clickThroughUrl') or {}).get('url', '')
                source = (content.get('provider') or {}).get('displayName', '')
            else:
                # 구버전 호환
                title  = item.get('title', '')
                url    = item.get('link', '')
                source = item.get('publisher', '')
            if title:
                news.append({'title': title, 'url': url, 'source': source})
    except Exception:
        pass

    return JsonResponse({
        'name':       name,
        'code':       code,
        'market':     'US',
        'price':      price,
        'change':     change,
        'change_pct': change_pct,
        'currency':   currency,
        'chart':      chart,
        'news':       news,
    })
