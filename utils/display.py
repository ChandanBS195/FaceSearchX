import sys
import os
from typing import List, Dict, Any

# Ensure stdout and stderr handle utf-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Try importing Rich; fallback to standard print if not installed
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    custom_theme = Theme({
        "info": "cyan bold",
        "success": "green bold",
        "warning": "yellow bold",
        "danger": "red bold",
        "highlight": "magenta bold",
        "title": "bold white on blue",
    })
    console = Console(theme=custom_theme, safe_box=True, legacy_windows=False)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

def print_banner():
    """Print Face Search X CLI Banner."""
    if HAS_RICH and console:
        banner_text = Text()
        banner_text.append(r" _____                          ____                               _        __  __ ", style="bold cyan")
        banner_text.append("\n", style="bold cyan")
        banner_text.append(r"|  ___|  __ _    ___    ___    / ___|    ___    __ _   _ __  ___  | |__     \ \/ / ", style="bold cyan")
        banner_text.append("\n", style="bold cyan")
        banner_text.append(r"| |_    / _` |  / __|  / _ \   \___ \   / _ \  / _` | | '_/ / __| | '_ \     \  /  ", style="bold blue")
        banner_text.append("\n", style="bold blue")
        banner_text.append(r"|  _|  | (_| | | (__  |  __/    ___) | |  __/ | (_| | | |  | (__  | | | |    /  \  ", style="bold blue")
        banner_text.append("\n", style="bold blue")
        banner_text.append(r"|_|     \__,_|  \___|  \___|   |____/   \___|  \__,_| |_|   \___| |_| |_|   /_/\_\ ", style="bold blue")
        banner_text.append("\n\n    [ Visual Face Discovery & Evidence Verification Pipeline Made By Chandan ]     ", style="bold yellow")
        console.print(Panel(banner_text, border_style="cyan", expand=False))
    else:
        print("\n==========================================================================================")
        print("                   F a c e   S e a r c h   X - Visual Face Discovery Pipeline")
        print("==========================================================================================\n")

def print_message(text: str, msg_type: str = "info"):
    """Print styled message or standard text fallback."""
    if HAS_RICH and console:
        console.print(f"[{msg_type}]{text}[/{msg_type}]")
    else:
        prefix_map = {"info": "[INFO]", "success": "[SUCCESS]", "warning": "[WARN]", "danger": "[ERROR]"}
        prefix = prefix_map.get(msg_type, "[INFO]")
        print(f"{prefix} {text}")

def print_step(step_num: int, title: str, status: str = "INFO"):
    """Print step header."""
    if HAS_RICH and console:
        style_map = {"INFO": "cyan", "SUCCESS": "green", "WARN": "yellow", "ERROR": "red"}
        color = style_map.get(status, "cyan")
        console.print(f"\n[{color}]> Stage {step_num}: {title}[/{color}]")
    else:
        print(f"\n--- Stage {step_num}: {title} ---")

def print_matches_table(verified_matches: List[Dict[str, Any]]):
    """Print clean table of candidate image URLs and domain-filtered page URL summaries."""
    from evidence.fingerprint import classify_social_domain

    if HAS_RICH and console:
        table = Table(title="Verified Face Candidate Images", border_style="green", show_lines=True)
        table.add_column("Rank", style="cyan", justify="center")
        table.add_column("Score", style="bold green", justify="center")
        table.add_column("Source Title", style="white", overflow="fold")
        table.add_column("Source Domain", style="yellow", overflow="fold")
        table.add_column("Candidate Image URL", style="magenta", overflow="fold")

        for match in verified_matches:
            rank = str(match.get("rank", "-"))
            pct = f"{match.get('similarity_pct', 0.0):.1f}%"
            title = match.get("title", "")
            source = match.get("source", "Web")
            img_url = match.get("image", "")
            table.add_row(rank, pct, title, source, img_url)

        console.print(table)

        # Categorize page URLs into Social Media vs General Web
        social_pages: Dict[tuple, int] = {}
        general_pages: Dict[tuple, int] = {}

        for match in verified_matches:
            source_name = match.get("source", "Web")
            page_url = match.get("link", "")
            if not page_url:
                continue
            platform, is_social = classify_social_domain(source_name, page_url)
            key = (platform, page_url)
            if is_social:
                social_pages[key] = social_pages.get(key, 0) + 1
            else:
                general_pages[key] = general_pages.get(key, 0) + 1

        if social_pages:
            console.print("\n[bold cyan]📱 Social Media Matches Identified (Domain Filtered):[/bold cyan]")
            for (plat, url), count in social_pages.items():
                img_str = "image" if count == 1 else "images"
                console.print(f"  * [bold green]{plat}[/bold green] ([cyan]{count} {img_str} matched[/cyan]): [blue underline]{url}[/blue underline]")

        if general_pages:
            console.print("\n[bold yellow]🌐 General Web & News Matches Identified:[/bold yellow]")
            for (src, url), count in general_pages.items():
                img_str = "image" if count == 1 else "images"
                console.print(f"  * [bold green]{src}[/bold green] ([cyan]{count} {img_str} matched[/cyan]): [blue underline]{url}[/blue underline]")
        console.print()
    else:
        print("\nVerified Face Candidate Images:")
        print(f"{'Rank':<5} | {'Score':<7} | {'Source Title':<35} | {'Domain':<15} | {'Candidate Image URL'}")
        print("-" * 110)
        for match in verified_matches:
            rank = str(match.get("rank", "-"))
            pct = f"{match.get('similarity_pct', 0.0):.1f}%"
            title = match.get("title", "")
            source = match.get("source", "Web")
            img_url = match.get("image", "")
            print(f"{rank:<5} | {pct:<7} | {title:<35} | {source:<15} | {img_url}")

        social_pages_std: Dict[tuple, int] = {}
        general_pages_std: Dict[tuple, int] = {}

        for match in verified_matches:
            source_name = match.get("source", "Web")
            page_url = match.get("link", "")
            if not page_url:
                continue
            platform, is_social = classify_social_domain(source_name, page_url)
            key = (platform, page_url)
            if is_social:
                social_pages_std[key] = social_pages_std.get(key, 0) + 1
            else:
                general_pages_std[key] = general_pages_std.get(key, 0) + 1

        if social_pages_std:
            print("\n📱 Social Media Matches Identified (Domain Filtered):")
            for (plat, url), count in social_pages_std.items():
                img_str = "image" if count == 1 else "images"
                print(f"  * {plat} ({count} {img_str} matched): {url}")

        if general_pages_std:
            print("\n🌐 General Web & News Matches Identified:")
            for (src, url), count in general_pages_std.items():
                img_str = "image" if count == 1 else "images"
                print(f"  * {src} ({count} {img_str} matched): {url}")
        print()

def print_evidence_card(evidence_record: Dict[str, Any]):
    """Print final evidence fingerprint card with social media summary."""
    payload = evidence_record["payload"]
    ev_hash = evidence_record["evidence_hash"]
    saved_path = evidence_record.get("saved_filepath", "")
    sm_summary = payload.get("social_media_summary", {})

    social_count = sm_summary.get("total_social_matches", 0)
    web_count = sm_summary.get("total_general_web_matches", 0)
    platforms_detected = sm_summary.get("platforms_detected", {})

    plat_str_list = [f"{plat} ({cnt})" for plat, cnt in platforms_detected.items()]
    plat_str = ", ".join(plat_str_list) if plat_str_list else "None"

    if HAS_RICH and console:
        card_text = Text()
        card_text.append("Evidence Fingerprint SHA-256:\n", style="bold yellow")
        card_text.append(f"{ev_hash}\n\n", style="bold green")
        card_text.append("* UTC Timestamp: ", style="bold white")
        card_text.append(f"{payload['timestamp_utc']}\n", style="cyan")
        card_text.append("* Input Source: ", style="bold white")
        card_text.append(f"{payload['input_source']}\n", style="cyan")
        card_text.append("* Detection Score: ", style="bold white")
        card_text.append(f"{payload['face_detection']['det_score']:.4f}\n", style="cyan")
        card_text.append("* Verified Face Matches: ", style="bold white")
        card_text.append(f"{payload['verified_matches_count']}\n", style="bold green")
        card_text.append("* Social Media Footprint: ", style="bold white")
        card_text.append(f"{social_count} match(es) [{plat_str}]\n", style="bold cyan")
        card_text.append("* General Web Matches: ", style="bold white")
        card_text.append(f"{web_count}\n", style="cyan")
        card_text.append("* Evidence Saved To: ", style="bold white")
        card_text.append(f"{saved_path}\n", style="magenta")

        console.print(Panel(card_text, title="[bold green]+ Evidence Record Generated (Stage 6 Fingerprint)[/bold green]", border_style="green"))
    else:
        print("\n==========================================================================")
        print("          + Evidence Record Generated (Stage 6 Fingerprint)")
        print("==========================================================================")
        print(f"Evidence Fingerprint SHA-256: {ev_hash}")
        print(f"* UTC Timestamp:           {payload['timestamp_utc']}")
        print(f"* Input Source:            {payload['input_source']}")
        print(f"* Detection Score:         {payload['face_detection']['det_score']:.4f}")
        print(f"* Verified Matches:        {payload['verified_matches_count']}")
        print(f"* Social Media Footprint:   {social_count} match(es) [{plat_str}]")
        print(f"* General Web Matches:     {web_count}")
        print(f"* Evidence File:           {saved_path}")
        print("==========================================================================\n")

if __name__ == "__main__":
    print_banner()

