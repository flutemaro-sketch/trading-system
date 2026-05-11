"""
表示モジュール

スコアリング結果を rich ライブラリで色付きの表として表示する。
仕様書の表示画面イメージを実現。
"""
from __future__ import annotations

from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .scoring import StockScore


def _score_color(score: int, max_score: int = 20) -> str:
    """スコアの大きさに応じた色を返す。"""
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= 0.7:
        return "bold green"
    if ratio >= 0.4:
        return "yellow"
    if ratio > 0:
        return "white"
    return "dim"


def _total_color(total: int) -> str:
    """合計スコアの色。"""
    if total >= 80:
        return "bold red"          # 最重要 = 赤強調
    if total >= 60:
        return "bold magenta"
    if total >= 40:
        return "bold yellow"
    if total >= 20:
        return "white"
    return "dim"


def render_ranking(
    scores: list[StockScore],
    title: str | None = None,
    top_n: int | None = None,
) -> None:
    """ランキングを rich で表示する。

    Args:
        scores: StockScore のリスト(降順ソート済)
        title: 表のタイトル(省略時は今日の日付)
        top_n: 上位N件のみ表示(省略時は全件)
    """
    console = Console()

    today = datetime.now().strftime("%Y/%m/%d")
    title = title or f"前日検討システム  {today}"

    target = scores[:top_n] if top_n else scores

    # メインのランキング表
    table = Table(
        title=title,
        title_style="bold cyan",
        box=box.ROUNDED,
        show_lines=False,
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("順", justify="right", width=3)
    table.add_column("らいおん", justify="right", width=6)
    table.add_column("差", justify="right", width=4)
    table.add_column("コード", justify="center", width=6)
    table.add_column("銘柄名", width=20)
    table.add_column("合計", justify="right", width=5)
    table.add_column("下駄", justify="right", width=4)
    table.add_column("出来高", justify="right", width=4)
    table.add_column("トレンド", justify="right", width=5)
    table.add_column("信用", justify="right", width=4)
    table.add_column("パターン", justify="right", width=5)
    table.add_column("加点", justify="right", width=4)
    table.add_column("主パターン", width=10)
    table.add_column("BB位置", width=10)
    table.add_column("決算", width=10)
    table.add_column("自社株買い", width=20)
    table.add_column("コメント", overflow="fold")

    for i, s in enumerate(target, 1):
        rank_style = "bold red" if i == 1 else ("bold yellow" if i <= 3 else "")

        # らいおん順位 と 順位差(秀長 - らいおん)を表示
        if s.lion_rank is not None:
            lion_str = str(s.lion_rank)
            diff = s.lion_rank - i  # +なら秀長で順位上昇、-なら下降
            if diff > 0:
                diff_str = f"↑{diff}"
                diff_style = "bold green"
            elif diff < 0:
                diff_str = f"↓{abs(diff)}"
                diff_style = "bold red"
            else:
                diff_str = "="
                diff_style = "white"
        else:
            lion_str = "-"
            diff_str = "-"
            diff_style = "dim"

        table.add_row(
            Text(str(i), style=rank_style),
            Text(lion_str, style="cyan"),
            Text(diff_str, style=diff_style),
            Text(s.code, style="cyan"),
            Text(s.name[:18] if s.name else "-", style="white"),
            Text(str(s.total), style=_total_color(s.total)),
            Text(str(s.geta), style=_score_color(s.geta)),
            Text(str(s.volume), style=_score_color(s.volume)),
            Text(str(s.trend), style=_score_color(s.trend)),
            Text(str(s.margin), style=_score_color(s.margin)),
            Text(str(s.island), style=_score_color(s.island)),
            Text(str(s.sector_bonus), style=_score_color(s.sector_bonus, 10)),
            Text(s.main_pattern, style="magenta"),
            Text(s.bb_position, style="bold red" if "[BB上限超]" in s.bb_position else "bold green" if "[BB下限超]" in s.bb_position else "white"),
            Text(s.settlement_alert, style="bold red" if "当日" in s.settlement_alert else "bold yellow" if "3日" in s.settlement_alert else "yellow"),
            Text(s.buyback_alert, style="bold green" if "底値スイング" in s.buyback_alert else "cyan" if "実施中" in s.buyback_alert else "yellow" if "実施待ち" in s.buyback_alert else "dim"),
            Text(s.comment, style="white"),
        )

    console.print()
    console.print(table)
    console.print()


def render_detail(s: StockScore) -> None:
    """1銘柄の詳細スコアを表示する。"""
    console = Console()
    detail_lines = [
        f"[cyan]銘柄:[/cyan] {s.code} {s.name}  ({s.sector})",
        f"[bold]合計スコア: {s.total}点[/bold]",
        "",
        f"  ① 下駄スコア:     {s.geta:>3}点  [{s.geta_note}]",
        f"  ② 出来高スコア:   {s.volume:>3}点  [{s.volume_note}]",
        f"  ③ トレンドスコア: {s.trend:>3}点  [{s.trend_note}]",
        f"  ④ 信用残スコア:   {s.margin:>3}点  [{s.margin_note}]",
        f"  ⑤ パターンスコア: {s.island:>3}点  [{s.island_note}]",
        f"  + セクター加点:   {s.sector_bonus:>3}点",
        "",
        f"  主パターン: {s.main_pattern}",
        f"  BB位置:   {s.bb_position}",
        f"  決算フラグ: {s.settlement_alert if s.settlement_alert else 'なし'}",
        f"  自社株買い: {s.buyback_alert if s.buyback_alert else 'なし'}",
        f"  コメント: {s.comment}",
    ]
    console.print(
        Panel(
            "\n".join(detail_lines),
            title=f"詳細 - {s.code}",
            border_style="cyan",
            expand=False,
        )
    )
