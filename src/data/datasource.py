# src/data/datasource.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DataSource(ABC):
    @abstractmethod
    def list_symbols(self) -> List[str]:
        pass

    @abstractmethod
    def get_bars(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_corporate_actions(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_earnings(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_news(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        pass

