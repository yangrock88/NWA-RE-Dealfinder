"""
Windows desktop + (optional) email notifications for new real estate deals.
Uses the same PowerShell toast approach proven in target_bot.
"""
import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def _toast(title: str, message: str, duration: str = "long") -> None:
    """Fire a Windows 10/11 toast notification via PowerShell."""
    ps_script = f"""
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$toastXml = [xml]$template.GetXml()
$toastXml.GetElementsByTagName("text")[0].AppendChild(
    $toastXml.CreateTextNode("{title}")) | Out-Null
$toastXml.GetElementsByTagName("text")[1].AppendChild(
    $toastXml.CreateTextNode("{message}")) | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($toastXml.OuterXml)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(
    "NWA Deal Finder").Show($toast)
""".strip().replace('"', '\\"')

    try:
        subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            capture_output=True, timeout=10,
        )
    except Exception as exc:
        log.debug("Toast notification failed: %s", exc)


def _beep() -> None:
    try:
        import winsound
        winsound.Beep(880, 300)
        winsound.Beep(1100, 300)
    except Exception:
        pass


def notify_new_deals(new_listings: list[dict]) -> None:
    """Desktop notification when new deals are found."""
    if not new_listings:
        return
    n = len(new_listings)
    top = new_listings[0]
    addr = top.get("address", "")
    price = top.get("price")
    price_str = f"${price:,.0f}" if price else "N/A"
    score = top.get("deal_score", 0)

    title = f"NWA Deal Finder — {n} New Deal{'s' if n > 1 else ''}!"
    body = f"{addr} | {price_str} | Score {score:.0f}"
    if n > 1:
        body += f" (+{n-1} more)"

    log.info("NOTIFICATION: %s — %s", title, body)
    _beep()
    _toast(title, body)


def notify_run_complete(total: int, deal_count: int) -> None:
    """Silent toast for a routine refresh (no new deals)."""
    title = "NWA Deal Finder — Refresh Complete"
    body = f"{total} listings scanned, {deal_count} deals found."
    log.info(body)
    _toast(title, body, duration="short")
