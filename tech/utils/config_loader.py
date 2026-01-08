#!/usr/bin/env python3
"""Configuration management for customer alert system.

Usage:
    from tech.utils.config_loader import Config

    config = Config.load('tech/config.json')

    # 访问配置
    margin = config.defaults.gross_margin
    churn_days = config.filters.default_churn_days
    high_value_threshold = config.customer_tiers.high_value.cumulative_threshold
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DotDict:
    """允许通过点号访问字典的包装类，支持嵌套。

    Example:
        d = DotDict({'a': {'b': 1}})
        print(d.a.b)  # 输出: 1
    """

    def __init__(self, data: Dict[str, Any]):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, DotDict(value))
            else:
                setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持默认值。"""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换回普通字典。"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, DotDict):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result


class Config:
    """配置管理类，提供类型安全的配置访问。"""

    def __init__(self, config_path: Path | str):
        self.config_path = Path(config_path)
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """从 JSON 文件加载配置。"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)

        # 转换为点号访问
        self.defaults = DotDict(self._data.get('defaults', {}))
        self.filters = DotDict(self._data.get('filters', {}))
        self.clv_weights = DotDict(self._data.get('clv_weights', {}))
        self.customer_tiers = DotDict(self._data.get('customer_tiers', {}))
        self.sku_alerts = DotDict(self._data.get('sku_alerts', {}))
        self.priority_score_boost = DotDict(self._data.get('priority_score_boost', {}))

        # 保持原始字典格式的部分
        self.categories = self._data.get('categories', {})
        self.platform_touch_cost = self._data.get('platform_touch_cost', {})
        self.orders_dampening = self._data.get('orders_dampening', {})
        self.single_order = self._data.get('single_order', {})

    @classmethod
    def load(cls, config_path: Path | str = 'tech/config.json') -> Config:
        """加载配置文件的便捷方法。

        Args:
            config_path: 配置文件路径，默认为 'tech/config.json'

        Returns:
            Config 实例
        """
        return cls(config_path)

    def get_category_config(self, preferred_item: str) -> Dict[str, Any]:
        """根据偏好单品获取品类配置。

        Args:
            preferred_item: 客户偏好单品名称

        Returns:
            品类配置字典，如果未匹配则返回 defaults
        """
        for category_name, category_config in self.categories.items():
            aliases = category_config.get('aliases', [])
            for alias in aliases:
                if alias in preferred_item:
                    return {
                        'category_name': category_name,
                        'gross_margin': category_config.get('gross_margin', self.defaults.gross_margin),
                        'category_cycle_days': category_config.get('category_cycle_days', self.defaults.category_cycle_days),
                        'expected_return_rate': category_config.get('expected_return_rate', self.defaults.expected_return_rate),
                        'touch_cost': category_config.get('touch_cost', self.defaults.touch_cost),
                        'max_estimated_margin': category_config.get('max_estimated_margin', self.defaults.max_estimated_margin),
                        'max_estimated_uplift': category_config.get('max_estimated_uplift', self.defaults.max_estimated_uplift),
                    }

        # 未匹配，返回默认配置
        return {
            'category_name': None,
            'gross_margin': self.defaults.gross_margin,
            'category_cycle_days': self.defaults.category_cycle_days,
            'expected_return_rate': self.defaults.expected_return_rate,
            'touch_cost': self.defaults.touch_cost,
            'max_estimated_margin': self.defaults.max_estimated_margin,
            'max_estimated_uplift': self.defaults.max_estimated_uplift,
        }

    def get_platform_touch_cost(self, platform: str) -> float:
        """获取平台触达成本。

        Args:
            platform: 平台名称（如 "小红书"、"抖音"）

        Returns:
            平台触达成本，未匹配则返回默认值
        """
        return self.platform_touch_cost.get(platform, self.defaults.touch_cost)

    def get_orders_dampening(self, order_count: int) -> float:
        """获取订单数对应的置信度权重。

        Args:
            order_count: 订单数量

        Returns:
            置信度权重 (0-1)
        """
        key = str(order_count)
        if key in self.orders_dampening:
            return self.orders_dampening[key]
        return self.orders_dampening.get('default', 1.0)

    def save(self, output_path: Optional[Path | str] = None) -> None:
        """保存配置到文件。

        Args:
            output_path: 输出路径，默认覆盖原文件
        """
        path = Path(output_path) if output_path else self.config_path

        # 重建完整的配置字典
        full_config = {
            'defaults': self.defaults.to_dict(),
            'filters': self.filters.to_dict(),
            'clv_weights': self.clv_weights.to_dict(),
            'customer_tiers': self.customer_tiers.to_dict(),
            'sku_alerts': self.sku_alerts.to_dict(),
            'priority_score_boost': self.priority_score_boost.to_dict(),
            'categories': self.categories,
            'platform_touch_cost': self.platform_touch_cost,
            'orders_dampening': self.orders_dampening,
            'single_order': self.single_order,
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(full_config, f, ensure_ascii=False, indent=2)

    def __repr__(self) -> str:
        return f"Config(path={self.config_path})"


# 便捷函数
def load_config(config_path: Path | str = 'tech/config.json') -> Config:
    """加载配置的便捷函数。"""
    return Config.load(config_path)


if __name__ == '__main__':
    # 测试代码
    import sys
    from pathlib import Path

    # 查找配置文件
    script_dir = Path(__file__).parent.parent
    config_file = script_dir / 'config.json'

    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)

    try:
        config = Config.load(config_file)

        print("✅ 配置文件加载成功！\n")
        print("=== 默认配置 ===")
        print(f"  毛利率: {config.defaults.gross_margin:.1%}")
        print(f"  品类周期: {config.defaults.category_cycle_days} 天")
        print(f"  预期退货率: {config.defaults.expected_return_rate:.1%}")
        print(f"  触达成本: ¥{config.defaults.touch_cost:.2f}")

        print("\n=== 过滤器配置 ===")
        print(f"  默认流失天数: {config.filters.default_churn_days} 天")
        print(f"  流失倍数: {config.filters.churn_multiplier}×")
        print(f"  冷却期: {config.filters.cooldown_days} 天")

        print("\n=== 客户层级阈值 ===")
        print(f"  高价值客户: ≥¥{config.customer_tiers.high_value.cumulative_threshold:,.0f}")
        print(f"  中价值客户: ¥{config.customer_tiers.medium_value.cumulative_min:,.0f} - ¥{config.customer_tiers.medium_value.cumulative_max:,.0f}")

        print("\n=== SKU 预警阈值 ===")
        print(f"  加推最低订单数: {config.sku_alerts.push_min_orders}")
        print(f"  加推最大退货率: {config.sku_alerts.push_max_return_rate:.0%}")
        print(f"  回看天数: {config.sku_alerts.push_lookback_days} 天")

        print("\n=== 品类配置 ===")
        for category in config.categories.keys():
            cat_config = config.get_category_config(category)
            print(f"  {category}: 毛利率 {cat_config['gross_margin']:.1%}, 周期 {cat_config['category_cycle_days']} 天")

        print("\n=== 平台触达成本 ===")
        for platform, cost in config.platform_touch_cost.items():
            print(f"  {platform}: ¥{cost:.2f}")

        print("\n✅ 所有配置项验证通过！")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
