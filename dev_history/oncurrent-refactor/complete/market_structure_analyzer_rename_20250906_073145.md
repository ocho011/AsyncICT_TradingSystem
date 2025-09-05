# `AsyncMarketStructure` 클래스 이름 변경 제안: `AsyncMarketStructureAnalyzer`

## 현재 상황

현재 `domain/entities/MarketStructure.py`에 정의된 `AsyncMarketStructure` 클래스는 캔들 데이터를 기반으로 BOS(Break of Structure) 및 CHoCH(Change of Character)를 감지하는 역할을 수행합니다. 그러나 `MarketStructure`라는 이름은 클래스의 능동적인 '분석' 또는 '탐지' 기능을 명확히 드러내지 못하고, 마치 시장 구조라는 정적인 데이터를 담는 엔티티처럼 느껴질 수 있다는 의견이 있었습니다.

## 문제점

*   **기능 불일치**: 클래스의 이름이 실제 수행하는 '분석' 및 '탐지' 역할과 완전히 일치하지 않아 모호함을 유발합니다.
*   **혼동 가능성**: `application/analysis/AsyncStructureBreakDetector.py`와 같이 상위 수준에서 시장 구조 변화를 탐지하고 조정하는 클래스와의 역할 구분이 이름만으로는 명확하지 않을 수 있습니다.

## 제안된 변경

`AsyncMarketStructure` 클래스의 이름을 `AsyncMarketStructureAnalyzer`로 변경할 것을 제안합니다.

## 변경의 이점

1.  **명확한 기능 반영**: `Analyzer`라는 접미사는 클래스가 데이터를 능동적으로 '분석'하고 '탐지'하는 역할을 수행한다는 점을 명확하게 전달합니다.

2.  **역할 분리 명확화**: 
    *   `AsyncStructureBreakDetector`: 여러 시간 프레임에 걸쳐 시장 구조 변화를 탐지하고, 각 시간 프레임별 분석기(`AsyncMarketStructureAnalyzer` 인스턴스)들을 관리하고 조정하는 상위 수준의 역할을 수행합니다.
    *   `AsyncMarketStructureAnalyzer`: 단일 시간 프레임에 대한 실제 시장 구조 분석(BOS, CHoCH 감지)을 수행하는 구체적인 분석기 역할을 합니다.
    이러한 이름 변경을 통해 두 클래스 간의 책임과 역할이 더욱 명확해집니다.

3.  **코드 가독성 및 의도 명확화**: 
    `AsyncStructureBreakDetector`가 `analyzers`라는 속성을 통해 `AsyncMarketStructureAnalyzer` 인스턴스들을 관리하게 되므로, 코드의 가독성이 높아지고 설계 의도가 더욱 분명해집니다.

## 결론

`AsyncMarketStructure`를 `AsyncMarketStructureAnalyzer`로 리팩토링하는 것은 클래스의 기능과 역할을 명확히 하고, `AsyncStructureBreakDetector`와의 혼동을 방지하며, 전반적인 코드의 가독성과 유지보수성을 크게 향상시킬 수 있는 매우 긍정적인 개선입니다.
