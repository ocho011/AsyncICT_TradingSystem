# Account Balance 설정 방식 분석

**날짜:** 2025-09-03 21:27:34

**작성자:** Gemini

## 개요

AsyncICT_TradingSystem에서 account balance가 거래소 잔고 확인이 아닌 config 파일을 통해 설정되는 이유에 대한 분석입니다.

## 현재 시스템 설계의 맥락

### Config 기반 잔고 설정 코드

```python
# AsyncTradingOrchestrator.py (63번째 줄)
self.account_balance = config.getfloat('account', 'balance')

# config.ini
[account]
balance = 10000.0
```

## 설정 방식의 이유

### 1. 안전한 시스템 테스트
- 실제 자금의 위험 없이 전체 거래 파이프라인을 검증
- 데이터 수신 → 분석 → 전략 판단 → 리스크 관리 → 주문 실행까지의 모든 로직 테스트 가능

### 2. 모의 거래 환경 구축
모의 거래 테스트 제안 문서(`메모_모의거래_테스트_제안_20250901.md`)에 따르면:
- `dry_run` 플래그를 통해 실제 주문과 모의 주문을 전환
- 실제 바이낸스 API 호출 대신 주문 상세 정보를 로그로 기록
- 주문이 즉시 '성공'으로 가정하고 다음 로직 진행

### 3. 리스크 관리 로직 검증
AsyncRiskManager에서 포지션 사이즈 계산 시 사용:

```python
def _calculate_position_size(self, stop_loss_price: float, entry_price: float) -> float:
    risk_amount = self.account_balance * self.risk_per_trade
    price_risk_per_unit = abs(entry_price - stop_loss_price)
    position_size = risk_amount / price_risk_per_unit
    return round(position_size, 3)
```

## 시스템 구조 분석

### 현재 AsyncBinanceRestClient의 한계
- 실제 계좌 잔고 확인을 위한 메소드(get_account_balance 등)가 구현되어 있지 않음
- REST API 엔드포인트(place_order, get_order 등)만 구현되어 있음

### AsyncRiskManager의 잔고 활용
- `account_balance`를 기반으로 포지션 사이즈 계산
- 리스크당 금액 = 계좌잔고 × 리스크비율(risk_per_trade)
- 포지션 크기 = 리스크금액 ÷ 가격리스크

## 실제 운영 시 변경 방향

### 1. 바이낸스 API 연동 필요
- `AsyncBinanceRestClient`에 잔고 확인 메소드 추가
- 바이낸스 Futures API의 계좌 정보 엔드포인트 활용

### 2. 실시간 잔고 조회 구현
- WebSocket을 통한 실시간 잔고 업데이트
- REST API를 통한 주기적 잔고 확인
- 잔고 변동 이벤트 처리

### 3. 동적 리스크 관리 적용
- 실제 잔고 변동에 따른 포지션 사이즈 실시간 조정
- 마진 레벨 및 liquidation price 모니터링
- 계좌 상태 기반 리스크 한도 동적 조정

## 결론

현재 config 기반 잔고 설정은 **시스템 개발 및 테스트 단계에서의 안전한 접근 방식**입니다. 실제 운영에서는 반드시 실제 거래소 API를 통한 실시간 잔고 조회로 전환해야 하며, 이는 향후 개발 단계에서 필수적으로 구현되어야 할 핵심 기능입니다.

## 관련 파일
- `application/orchestration/AsyncTradingOrchestrator.py`
- `application/execution/AsyncRiskManager.py`
- `infrastructure/binance/AsyncBinanceRestClient.py`
- `config.ini`
- `dev_history/proposed/메모_모의거래_테스트_제안_20250901.md`
