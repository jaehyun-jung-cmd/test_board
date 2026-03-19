"""
주식조회 뷰 테스트 (TDD)

외부 API는 unittest.mock.patch로 모킹하여 실제 네트워크 없이 테스트.
- Naver Finance API: requests.get 모킹
- yfinance: yfinance.Ticker 모킹
"""
import json
from unittest.mock import patch, MagicMock

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


# ─── Naver API 모킹 픽스처 ──────────────────────────────────────────────

@pytest.fixture
def mock_naver_search():
    """Naver 자동완성 API 응답 모킹"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            [["005930", "삼성전자", "0", "코스피", "005930"]],
        ]
    }
    with patch('requests.get', return_value=mock_resp):
        yield mock_resp


@pytest.fixture
def mock_naver_apis():
    """Naver 시세·차트·뉴스 API 모킹 (api_quote KR)"""
    def _get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if 'basic' in url:
            resp.json.return_value = {
                "stockName": "삼성전자",
                "closePrice": "75000",
                "compareToPreviousClosePrice": "500",
                "fluctuationsRatio": "0.67",
            }
        elif 'chart' in url:
            resp.json.return_value = {
                "result": {
                    "itemChartPrices": [
                        {"localDate": "20240101", "closePrice": 70000},
                        {"localDate": "20240201", "closePrice": 72000},
                        {"localDate": "20240301", "closePrice": 75000},
                    ]
                }
            }
        elif 'news' in url:
            resp.json.return_value = {
                "result": {
                    "newsList": [
                        {"title": "삼성전자 뉴스1", "url": "https://n.news.naver.com/1", "officeName": "한국경제"},
                        {"title": "삼성전자 뉴스2", "url": "https://n.news.naver.com/2", "officeName": "조선일보"},
                    ]
                }
            }
        return resp

    with patch('requests.get', side_effect=_get):
        yield


@pytest.fixture
def mock_naver_404():
    """Naver 시세 API 404 응답 모킹"""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch('requests.get', return_value=mock_resp):
        yield


@pytest.fixture
def mock_naver_partial():
    """Naver 시세는 성공, 차트·뉴스는 예외 발생 모킹"""
    def _get(url, **kwargs):
        resp = MagicMock()
        if 'basic' in url:
            resp.status_code = 200
            resp.json.return_value = {
                "stockName": "삼성전자",
                "closePrice": "75000",
                "compareToPreviousClosePrice": "500",
                "fluctuationsRatio": "0.67",
            }
        else:
            raise Exception("network error")
        return resp

    with patch('requests.get', side_effect=_get):
        yield


# ─── yfinance 모킹 픽스처 ────────────────────────────────────────────────

@pytest.fixture
def mock_yfinance():
    """yfinance.Ticker 모킹 (US 종목 정상)"""
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "shortName": "Apple Inc.",
        "currentPrice": 185.5,
        "regularMarketChange": 1.23,
        "regularMarketChangePercent": 0.67,
        "currency": "USD",
    }

    import pandas as pd
    dates = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"])
    hist = pd.DataFrame({"Close": [170.0, 178.5, 185.5]}, index=dates)
    mock_ticker.history.return_value = hist

    mock_ticker.news = [
        {"title": "Apple News 1", "link": "https://finance.yahoo.com/1", "publisher": "Reuters"},
        {"title": "Apple News 2", "link": "https://finance.yahoo.com/2", "publisher": "Bloomberg"},
    ]

    with patch('yfinance.Ticker', return_value=mock_ticker):
        yield mock_ticker


@pytest.fixture
def mock_yfinance_empty():
    """yfinance.Ticker 모킹 - 알 수 없는 티커 (info 비어있음)"""
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    mock_ticker.history.return_value = MagicMock()
    mock_ticker.history.return_value.empty = True

    with patch('yfinance.Ticker', return_value=mock_ticker):
        yield mock_ticker


# ─── 테스트 케이스 ────────────────────────────────────────────────────────

class TestStocksIndex:
    """GET /stocks/ 인덱스 페이지 테스트"""

    def test_stocks_index_returns_200(self, client):
        """GET /stocks/ → 200 OK, index 템플릿 렌더링"""
        response = client.get('/stocks/')
        assert response.status_code == 200
        assert b'stocks/index.html' in response.content or \
               response.templates[0].name == 'stocks/index.html'


class TestApiSearch:
    """GET /stocks/api/search/ 자동완성 테스트"""

    def test_api_search_kr_returns_results(self, client, mock_naver_search):
        """GET /stocks/api/search/?q=삼성 → Naver API 결과 JSON 반환"""
        response = client.get('/stocks/api/search/?q=삼성')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert 'results' in data
        assert len(data['results']) > 0
        assert data['results'][0]['code'] == '005930'
        assert data['results'][0]['name'] == '삼성전자'

    def test_api_search_empty_query(self, client):
        """GET /stocks/api/search/ (q 없음) → 빈 results"""
        response = client.get('/stocks/api/search/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == {'results': []}


class TestApiQuote:
    """GET /stocks/api/quote/ 시세 조회 테스트"""

    def test_api_quote_kr_success(self, client, mock_naver_apis):
        """GET /stocks/api/quote/?market=KR&code=005930 → 시세+차트+뉴스 JSON"""
        response = client.get('/stocks/api/quote/?market=KR&code=005930')
        assert response.status_code == 200
        data = json.loads(response.content)

        assert data['name'] == '삼성전자'
        assert data['code'] == '005930'
        assert data['market'] == 'KR'
        assert data['price'] == '75000'
        assert data['currency'] == 'KRW'
        assert 'chart' in data
        assert 'dates' in data['chart']
        assert 'prices' in data['chart']
        assert 'news' in data
        assert len(data['news']) > 0

    def test_api_quote_us_success(self, client, mock_yfinance):
        """GET /stocks/api/quote/?market=US&code=AAPL → yfinance 결과 JSON"""
        response = client.get('/stocks/api/quote/?market=US&code=AAPL')
        assert response.status_code == 200
        data = json.loads(response.content)

        assert data['name'] == 'Apple Inc.'
        assert data['code'] == 'AAPL'
        assert data['market'] == 'US'
        assert data['price'] == 185.5
        assert data['currency'] == 'USD'
        assert 'chart' in data
        assert 'news' in data

    def test_api_quote_missing_code(self, client):
        """GET /stocks/api/quote/ (code 없음) → 400"""
        response = client.get('/stocks/api/quote/')
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data

    def test_api_quote_kr_not_found(self, client, mock_naver_404):
        """Naver API 404 → 404 응답"""
        response = client.get('/stocks/api/quote/?market=KR&code=INVALID')
        assert response.status_code == 404
        data = json.loads(response.content)
        assert 'error' in data

    def test_api_quote_us_not_found(self, client, mock_yfinance_empty):
        """yfinance 알 수 없는 티커 → 404 응답"""
        response = client.get('/stocks/api/quote/?market=US&code=INVALID')
        assert response.status_code == 404
        data = json.loads(response.content)
        assert 'error' in data

    def test_api_quote_kr_chart_failure_still_returns_price(self, client, mock_naver_partial):
        """Naver 차트/뉴스 실패 시에도 시세는 정상 반환 (비핵심 데이터 무시)"""
        response = client.get('/stocks/api/quote/?market=KR&code=005930')
        assert response.status_code == 200
        data = json.loads(response.content)

        assert data['price'] == '75000'
        assert data['chart'] == {'dates': [], 'prices': []}
        assert data['news'] == []
