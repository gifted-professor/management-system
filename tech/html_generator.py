#!/usr/bin/env python3
"""HTML Generator using Jinja2 Templates.

This module provides functions to generate HTML dashboard using Jinja2 templates,
replacing the inline HTML generation in generate_customer_alerts.py.

Usage:
    from tech.html_generator import render_dashboard

    html = render_dashboard(
        today=date.today(),
        action_rows=action_rows,
        global_details=global_details,
        # ... other parameters
    )
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape


class DashboardRenderer:
    """HTML Dashboard Renderer using Jinja2 templates."""

    def __init__(self, template_dir: Optional[Path | str] = None):
        """Initialize the renderer with template directory.

        Args:
            template_dir: Path to templates directory. If None, uses tech/templates/
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / 'templates'

        self.template_dir = Path(template_dir)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_dashboard(
        self,
        today: date,
        action_rows: List[Dict[str, Any]],
        filters_html: str = '',
        header_cells: str = '',
        table_rows: str = '',
        sku_push_html: str = '',
        sku_return_html: str = '',
        low_margin_html: str = '',
        tags: List[str] = None,
        platforms: List[str] = None,
        detail_map: Dict[str, List[Dict[str, Any]]] = None,
        global_details: Dict[str, List[Dict[str, Any]]] = None,
        global_meta: Dict[str, Dict[str, Any]] = None,
        id_index: Dict[str, str] = None,
        name_index: Dict[str, str] = None,
        cooldown_keys: List[str] = None,
        cooldown_customers: Dict[str, date] = None,
        cooldown_days: int = 7,
        cooldown_total: int = 0,
        contact_server_port: int = 8081,
        contact_write_enabled: bool = False,
        owner_suggestions: List[str] = None,
        env_default_owner: str = '',
    ) -> str:
        """Render the complete dashboard HTML.

        Args:
            today: Today's date
            action_rows: List of customer action rows
            filters_html: Pre-rendered filters HTML
            header_cells: Pre-rendered table header cells
            table_rows: Pre-rendered table rows
            sku_push_html: SKU push recommendations HTML
            sku_return_html: High return rate SKU HTML
            low_margin_html: Low margin SKU HTML
            tags: List of risk tags
            platforms: List of platforms
            detail_map: Map of customer key to order details
            global_details: Global order details
            global_meta: Global customer metadata
            id_index: Index mapping order IDs to customer keys
            name_index: Index mapping names to customer keys
            cooldown_keys: List of cooldown customer keys
            cooldown_customers: Map of customer key to last contact date
            cooldown_days: Cooldown period in days
            cooldown_total: Total cooldown customers
            contact_server_port: Contact server port
            contact_write_enabled: Whether contact write is enabled
            owner_suggestions: List of owner name suggestions
            env_default_owner: Default owner from environment

        Returns:
            Complete HTML string
        """
        # Calculate statistics
        high_priority_count = sum(1 for row in action_rows if row.get('priority_score', 0) >= 80)
        mid_priority_count = sum(1 for row in action_rows if 50 <= row.get('priority_score', 0) < 80)
        total_customers = len(action_rows)

        # Serialize data to JSON for JavaScript
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        platforms_json = json.dumps(platforms or [], ensure_ascii=False)
        detail_map_json = json.dumps(detail_map or {}, ensure_ascii=False, separators=(',', ':'))
        global_details_json = json.dumps(global_details or {}, ensure_ascii=False, separators=(',', ':'))
        global_meta_json = json.dumps(global_meta or {}, ensure_ascii=False, separators=(',', ':'))
        id_index_json = json.dumps(id_index or {}, ensure_ascii=False, separators=(',', ':'))
        name_index_json = json.dumps(name_index or {}, ensure_ascii=False, separators=(',', ':'))
        cooldown_keys_json = json.dumps(cooldown_keys or [], ensure_ascii=False)

        # Convert cooldown_customers dates to ISO strings
        cooldown_customers_serializable = {}
        if cooldown_customers:
            for key, dt in cooldown_customers.items():
                if isinstance(dt, date):
                    cooldown_customers_serializable[key] = dt.isoformat()
                else:
                    cooldown_customers_serializable[key] = str(dt)
        cooldown_customers_json = json.dumps(cooldown_customers_serializable, ensure_ascii=False)

        owner_suggestions_json = json.dumps(owner_suggestions or [], ensure_ascii=False)
        env_default_owner_json = json.dumps(env_default_owner, ensure_ascii=False)

        # Render template
        template = self.env.get_template('dashboard.html')

        html = template.render(
            today=today.isoformat(),
            high_priority_count=high_priority_count,
            mid_priority_count=mid_priority_count,
            total_customers=total_customers,
            cooldown_total=cooldown_total,
            cooldown_days=cooldown_days,
            filters_html=filters_html,
            header_cells=header_cells,
            table_rows=table_rows,
            sku_push_html=sku_push_html,
            sku_return_html=sku_return_html,
            low_margin_html=low_margin_html,
            # JSON data
            tags_json=tags_json,
            platforms_json=platforms_json,
            detail_map_json=detail_map_json,
            global_details_json=global_details_json,
            global_meta_json=global_meta_json,
            id_index_json=id_index_json,
            name_index_json=name_index_json,
            cooldown_keys_json=cooldown_keys_json,
            cooldown_customers_json=cooldown_customers_json,
            owner_suggestions_json=owner_suggestions_json,
            env_default_owner_json=env_default_owner_json,
            # Config
            contact_server_port=contact_server_port,
            contact_write_enabled=contact_write_enabled,
        )

        return html


# Convenience function
def render_dashboard(**kwargs) -> str:
    """Render dashboard HTML using default template directory.

    See DashboardRenderer.render_dashboard() for parameter documentation.

    Returns:
        Complete HTML string
    """
    renderer = DashboardRenderer()
    return renderer.render_dashboard(**kwargs)


if __name__ == '__main__':
    # Test the template system
    from datetime import date

    print("Testing HTML template rendering...")

    try:
        html = render_dashboard(
            today=date.today(),
            action_rows=[],
            filters_html='<div class="filters">Test Filters</div>',
            header_cells='<th>Test Header</th>',
            table_rows='<tr><td>Test Row</td></tr>',
            sku_push_html='<div>SKU Push</div>',
            sku_return_html='<div>SKU Return</div>',
            low_margin_html='<div>Low Margin</div>',
        )

        print(f"✅ Template rendered successfully ({len(html)} characters)")
        print(f"   Contains <html>: {'<html' in html}")
        print(f"   Contains <body>: {'<body' in html}")
        print(f"   Contains dashboard: {'仪表盘' in html}")

    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        import traceback
        traceback.print_exc()
