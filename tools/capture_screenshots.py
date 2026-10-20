#!/usr/bin/env python3
"""Interactively capture real PsyConsult UI screenshots and embed them in README."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("缺少 Playwright。请先运行：")
    print("  python -m pip install playwright")
    print("  python -m playwright install chromium")
    raise SystemExit(2)

ROOT = Path.cwd()
OUT = ROOT / "docs" / "screenshots"
README = ROOT / "README.md"
START = "<!-- SCREENSHOTS_START -->"
END = "<!-- SCREENSHOTS_END -->"

SCREENS = [
    ("01-chat", "聊天主界面"),
    ("02-assessment", "心理健康自评"),
    ("03-patient-archive", "患者档案"),
    ("04-report-analysis", "心理测评报告分析"),
    ("05-recording", "录音转写"),
]


def update_readme(captured: list[tuple[str, str]]) -> None:
    if not README.exists():
        print("未找到根目录 README.md，截图已保存，但没有自动更新文档。")
        return

    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("README 缺少截图标记，截图已保存，但没有自动更新文档。")
        return

    if not captured:
        body = "本次没有生成截图。请使用虚构测试数据重新运行截图脚本。"
    else:
        parts = []
        for slug, label in captured:
            parts.append(f"### {label}\n\n![{label}](docs/screenshots/{slug}.png)")
        body = "\n\n".join(parts)

    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(
        before + START + "\n" + body + "\n" + END + after,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5173", help="本地前端地址")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    if not README.exists() or not (ROOT / "front" / "clinical_cds").exists():
        print("请在 PsyConsult 仓库根目录运行此脚本。")
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    captured: list[tuple[str, str]] = []

    print("即将打开真实的本地 PsyConsult 页面。")
    print("请只使用虚构测试档案；截屏前确认没有真实个人信息、报告正文、令牌或敏感路径。")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=1,
        )
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            print(f"页面打开提示：{exc}")
            print("如果页面未打开，请确认前端正在运行，再在浏览器中打开目标地址。")

        for slug, label in SCREENS:
            answer = input(
                f"\n请在打开的浏览器中切换到「{label}」页面，检查内容后按回车截图；"
                "输入 skip 跳过："
            ).strip().lower()
            if answer == "skip":
                print("已跳过。")
                continue

            # 不记录页面文本或表单内容，只保存用户确认后的屏幕画面。
            path = OUT / f"{slug}.png"
            try:
                page.screenshot(path=str(path), full_page=True, animations="disabled")
                captured.append((slug, label))
                print("已保存：", path.relative_to(ROOT))
            except Exception as exc:
                print(f"截图失败：{exc}")

        browser.close()

    update_readme(captured)
    print(f"\n本次生成截图：{len(captured)} 张")
    print("请逐张检查截图，再运行 git status、Gitleaks 与发布前自查。")
    print("不要把真实患者信息打码后继续公开；优先使用纯虚构测试数据重新截图。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
