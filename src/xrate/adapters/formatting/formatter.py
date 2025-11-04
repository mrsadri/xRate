# src/xrate/adapters/formatting/formatter.py
"""
Message Formatter - Text Formatting and Presentation

This module handles all text formatting for Telegram messages, including
market data display, percentage changes, elapsed time formatting, and
various message layouts for different bot commands.

Files that USE this module:
- xrate.adapters.telegram.handlers (uses all formatter functions for message display)
- xrate.adapters.telegram.jobs (uses market_lines and market_lines_with_changes)
- tests.test_formatter (unit tests)

Files that this module USES:
- xrate.domain.models (IrrSnapshot for market data structures)
- xrate.shared.language (translate for multi-language support)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from xrate.domain.models import IrrSnapshot
from xrate.shared.language import translate, format_persian_number, get_language, LANG_FARSI


def format_irr_snapshot(title: str, snap: Optional[IrrSnapshot]) -> str:
    """
    Format IRR snapshot data as a plain text message.
    
    Args:
        title: Title for the snapshot
        snap: IrrSnapshot data to format (can be None)
        
    Returns:
        Formatted string with USD, EUR, and Gold prices, or "N/A" if snap is None
    """
    if snap is None:
        return f"{title}\n— USD: N/A\n— EUR: N/A\n— 18k Gold (1g): N/A"
    
    # Plain text, no code fences
    return (
        f"{title}\n"
        f"— USD: {snap.usd_toman}\n"
        f"— EUR: {snap.eur_toman}\n"
        f"— 18k Gold (1g): {snap.gold_1g_toman}"
    )


def eur_usd(rate: float, decimals: int = 4, with_time: bool = False) -> str:
    """
    Format EUR/USD exchange rate as a message.
    
    Args:
        rate: USD per 1 EUR rate
        decimals: Number of decimal places (default: 4)
        with_time: Whether to include timestamp (default: False)
        
    Returns:
        Formatted string showing EUR/USD rate
    """
    msg = f"💶 1 Euro = ${rate:.{decimals}f} USD"
    if with_time:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        msg = f"{msg}\n⏱️ {now}"
    return msg


def market_lines(snap: Optional[IrrSnapshot], eur_usd_rate: Optional[float], 
                providers: Optional[List[str]] = None) -> str:
    """
    Format market data as simple text lines without percentage changes.
    
    Formats USD, EUR, Gold prices, and EUR/USD rate as plain text.
    Handles missing data gracefully by showing N/A for unavailable providers.
    
    Args:
        snap: Optional IrrSnapshot with market data
        eur_usd_rate: Optional EUR/USD exchange rate
        providers: Optional list of provider names that provided the data
        
    Returns:
        Formatted multi-line string with market rates
        
    Note:
        Without monospace, spacing/alignment may vary per device/font.
    """
    lines = []
    
    if snap:
        usd_kilo = snap.usd_toman / 1000
        eur_kilo = snap.eur_toman / 1000
        gold_million = snap.gold_1g_toman / 1_000_000
        lines.append(translate("usd_line", value=f"{usd_kilo:.1f}", change=""))
        lines.append(translate("eur_line", value=f"{eur_kilo:.1f}", change=""))
        lines.append(translate("gold_line", value=f"{gold_million:.3f}", change=""))
    else:
        lines.append(translate("usd_line", value="N/A ⚠️", change=""))
        lines.append(translate("eur_line", value="N/A ⚠️", change=""))
        lines.append(translate("gold_line", value="N/A ⚠️", change=""))
    
    if eur_usd_rate is not None:
        lines.append(translate("eurusd_line", value=f"{eur_usd_rate:.4f}", change=""))
    else:
        lines.append(translate("eurusd_line", value="N/A ⚠️", change=""))
    
    # Add provider attribution if provided
    if providers and len(providers) > 0:
        provider_names = " and ".join(providers)
        lines.append(translate("reported_by", providers=provider_names))
    
    return "\n".join(lines)


# -------- with % change and elapsed time (plain text) --------

def _fmt_pct(curr: float, prev: float) -> str:
    """
    Format percentage change between current and previous values.
    
    Formula: (new - old) / old * 100
    - Positive delta = price increased = 📈
    - Negative delta = price decreased = 📉
    
    Args:
        curr: Current value (new)
        prev: Previous/baseline value (old)
        
    Returns:
        Formatted string like '2.1% 📈', '3.1% 📉', '0.0% ⏸', or '—' if prev <= 0
    """
    if prev <= 0:
        return "—"  # Guard: cannot calculate % change with invalid baseline
    delta = (curr - prev) / prev * 100.0
    arrow = "📈" if delta > 0 else ("📉" if delta < 0 else "⏸")
    return f"{abs(delta):.1f}% {arrow}"


def _fmt_elapsed(seconds: int) -> str:
    """
    Format elapsed time as 'Xh:YYmin' or 'Ymin'.
    
    Args:
        seconds: Elapsed time in seconds (will be clamped to >= 0)
        
    Returns:
        Formatted string like '2h:42min' or '5min'
    """
    if seconds < 0:
        seconds = 0
    minutes = seconds // 60
    hours = minutes // 60
    mins_only = minutes % 60
    if hours > 0:
        return f"{hours}h:{mins_only:02d}min"
    return f"{mins_only}min"


def market_lines_with_changes(
    curr: Optional[IrrSnapshot],
    curr_eur_usd: Optional[float],
    prev_usd_toman: Optional[int],
    prev_eur_toman: Optional[int],
    prev_gold_1g_toman: Optional[int],
    prev_eur_usd: Optional[float],
    elapsed_seconds: int,
    show_usd: bool = True,
    show_eur: bool = True,
    show_gold: bool = True,
    show_eurusd: bool = True,
    tether_price_toman: Optional[int] = None,
    tether_24h_ch: Optional[float] = None,
    show_tether: bool = False,
    providers: Optional[List[str]] = None,
) -> str:
    """
    Format market data with percentage changes and elapsed time.
    
    Produces lines showing current rates, percentage changes vs previous values,
    and elapsed time since last announcement. Only shows items that have breached
    their thresholds (smart formatting).
    
    Args:
        curr: Optional current market snapshot
        curr_eur_usd: Optional current EUR/USD rate
        prev_usd_toman: Optional previous USD price in Toman
        prev_eur_toman: Optional previous EUR price in Toman
        prev_gold_1g_toman: Optional previous 18K gold price per gram
        prev_eur_usd: Optional previous EUR/USD rate
        elapsed_seconds: Seconds elapsed since last announcement
        show_usd: Whether to include USD line (default: True)
        show_eur: Whether to include EUR line (default: True)
        show_gold: Whether to include Gold line (default: True)
        show_eurusd: Whether to include EUR/USD line (default: True)
        tether_price_toman: Optional Tether price in Toman
        tether_24h_ch: Optional Tether 24-hour change percentage
        show_tether: Whether to include Tether line (default: False)
        providers: Optional list of provider names that provided the data
        
    Returns:
        Formatted multi-line string with rates, changes, and elapsed time
        
    Note:
        Handles missing data gracefully. Spacing is best-effort in proportional fonts.
        Only items with show_* flags set to True will be included in the output.
    """
    lines = []
    
    # USD line
    if show_usd and curr:
        usd_k = curr.usd_toman / 1000
        usd_pct = _fmt_pct(curr.usd_toman, prev_usd_toman or 0)
        lines.append(translate("usd_line", value=f"{usd_k:.1f}", change=usd_pct))
    
    # EUR line
    if show_eur and curr:
        eur_k = curr.eur_toman / 1000
        eur_pct = _fmt_pct(curr.eur_toman, prev_eur_toman or 0)
        lines.append(translate("eur_line", value=f"{eur_k:.1f}", change=eur_pct))
    
    # Gold line
    if show_gold and curr:
        gold_m = curr.gold_1g_toman / 1_000_000
        gold_pct = _fmt_pct(curr.gold_1g_toman, prev_gold_1g_toman or 0)
        lines.append(translate("gold_line", value=f"{gold_m:.3f}", change=gold_pct))
    
    # EUR/USD line
    if show_eurusd and curr_eur_usd is not None:
        fx_pct = _fmt_pct(curr_eur_usd, prev_eur_usd or 0.0)
        lines.append(translate("eurusd_line", value=f"{curr_eur_usd:.4f}", change=fx_pct))
    
    # Tether line
    if show_tether and tether_price_toman is not None and tether_24h_ch is not None:
        tether_k = tether_price_toman / 1000
        tether_arrow = "📈" if tether_24h_ch > 0 else ("📉" if tether_24h_ch < 0 else "⏸")
        lines.append(translate("tether_line", value=f"{tether_k:.1f}", change_pct=f"{abs(tether_24h_ch):.2f}", arrow=tether_arrow))
    
    # Always show elapsed time if we have at least one line
    if lines:
        elapsed = _fmt_elapsed(int(elapsed_seconds))
        lines.append(translate("time_elapsed", elapsed=elapsed))
    
    # Add provider attribution if provided
    if providers and len(providers) > 0:
        provider_names = " and ".join(providers)
        lines.append(translate("reported_by", providers=provider_names))
    
    return "\n".join(lines) if lines else translate("no_data")


def format_persian_market_update(
    curr: Optional[IrrSnapshot],
    prev_usd_toman: Optional[int],
    prev_eur_toman: Optional[int],
    prev_gold_1g_toman: Optional[int],
    elapsed_seconds: int,
) -> str:
    """
    Format market update in Persian format as specified.
    
    Format:
    نوسان جدید نبش بازار مشاهده شد
    
    دلار: ۱۰۸ هزار و ۵۰۰ تومان        1.0% 📉
    یورو : ۱۲۴ هزار و ۲۰۰ تومان         0.0% ⏸
    طلا: ۱۰ میلیون و  ۵۳۱ هزار تومن     0.1% 📈
    
    مدت آرامش بازار: ۱ ساعت و ۲۰ دقیقه
    
    Args:
        curr: Current market snapshot
        prev_usd_toman: Previous USD price
        prev_eur_toman: Previous EUR price
        prev_gold_1g_toman: Previous Gold price
        elapsed_seconds: Elapsed time since last update
        
    Returns:
        Formatted Persian message
    """
    if not curr:
        return translate("no_data")
    
    lines = []
    lines.append(translate("market_update_header"))
    lines.append("")  # Empty line
    
    # USD
    usd_formatted = format_persian_number(curr.usd_toman) + " تومان"
    usd_pct = _fmt_pct(curr.usd_toman, prev_usd_toman or 0)
    lines.append(translate("usd_line", value=usd_formatted, change=usd_pct))
    
    # EUR
    eur_formatted = format_persian_number(curr.eur_toman) + " تومان"
    eur_pct = _fmt_pct(curr.eur_toman, prev_eur_toman or 0)
    lines.append(translate("eur_line", value=eur_formatted, change=eur_pct))
    
    # Gold
    gold_formatted = format_persian_number(curr.gold_1g_toman) + " تومن"
    gold_pct = _fmt_pct(curr.gold_1g_toman, prev_gold_1g_toman or 0)
    lines.append(translate("gold_line", value=gold_formatted, change=gold_pct))
    
    lines.append("")  # Empty line
    
    # Elapsed time in Persian
    elapsed = _fmt_elapsed_persian(elapsed_seconds)
    lines.append(translate("time_elapsed", elapsed=elapsed))
    
    return "\n".join(lines)


def format_persian_daily_report(
    curr: Optional[IrrSnapshot],
    elapsed_seconds: int,
) -> str:
    """
    Format daily report in Persian format.
    
    Format:
    گزارش روزانه قیمت‌ها:
    
    دلار: ۱۰۸ هزار و ۵۰۰ تومان        
    یورو : ۱۲۴ هزار و ۲۰۰ تومان         
    طلا: ۱۰ میلیون و  ۵۳۱ هزار تومن   
    
    مدت آرامش بازار: ۱ ساعت و ۲۰ دقیقه
    
    Args:
        curr: Current market snapshot
        elapsed_seconds: Elapsed time since last update
        
    Returns:
        Formatted Persian daily report
    """
    if not curr:
        return translate("no_data")
    
    lines = []
    lines.append(translate("daily_report_header"))
    lines.append("")  # Empty line
    
    # USD
    usd_formatted = format_persian_number(curr.usd_toman) + " تومان"
    lines.append(translate("usd_line", value=usd_formatted, change=""))
    
    # EUR
    eur_formatted = format_persian_number(curr.eur_toman) + " تومان"
    lines.append(translate("eur_line", value=eur_formatted, change=""))
    
    # Gold
    gold_formatted = format_persian_number(curr.gold_1g_toman) + " تومن"
    lines.append(translate("gold_line", value=gold_formatted, change=""))
    
    lines.append("")  # Empty line
    
    # Elapsed time in Persian
    elapsed = _fmt_elapsed_persian(elapsed_seconds)
    lines.append(translate("time_elapsed", elapsed=elapsed))
    
    return "\n".join(lines)


def _fmt_elapsed_persian(seconds: int) -> str:
    """
    Format elapsed time in Persian: "X ساعت و Y دقیقه" or "Y دقیقه"
    
    Args:
        seconds: Elapsed time in seconds
        
    Returns:
        Formatted Persian time string
    """
    if seconds < 0:
        seconds = 0
    minutes = seconds // 60
    hours = minutes // 60
    mins_only = minutes % 60
    
    if hours > 0 and mins_only > 0:
        return f"{hours} ساعت و {mins_only} دقیقه"
    elif hours > 0:
        return f"{hours} ساعت"
    else:
        return f"{mins_only} دقیقه"
