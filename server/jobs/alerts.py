"""Job alert subscriptions and the run that delivers them."""
from server.channels.db import connect
from server.channels.strings import norm_lang, t

from .store import format_job, format_job_sms, load_jobs, matches

MAX_PER_RUN = 3  # per subscription, so nobody gets a flood


def subscribe(channel: str, address: str, keyword: str, language: str) -> str:
    """Add (or refresh) a subscription. Returns the stored keyword ('*' means every job)."""
    keyword = " ".join((keyword or "").lower().split())[:40] or "*"
    with connect() as c:
        c.execute(
            "INSERT INTO subscriptions (channel, address, keyword, language) VALUES (?,?,?,?) "
            "ON CONFLICT(channel, address, keyword) DO UPDATE SET language=excluded.language",
            (channel, str(address), keyword, norm_lang(language)),
        )
    return keyword


def unsubscribe(channel: str, address: str) -> int:
    """Remove every subscription of this address. Returns how many were removed."""
    with connect() as c:
        ids = [r["id"] for r in c.execute(
            "SELECT id FROM subscriptions WHERE channel=? AND address=?", (channel, str(address)))]
        for sub_id in ids:
            c.execute("DELETE FROM sent_alerts WHERE subscription_id=?", (sub_id,))
        c.execute("DELETE FROM subscriptions WHERE channel=? AND address=?", (channel, str(address)))
    return len(ids)


def confirmation(keyword: str, lang: str) -> str:
    return t(lang, "subscribed_all") if keyword == "*" else t(lang, "subscribed", keyword=keyword)


async def _deliver(sub, job) -> bool:
    lang = sub["language"]
    if sub["channel"] == "sms":
        from server.channels.sms import queue_sms

        queue_sms(sub["address"], t(lang, "job_alert_prefix") + ": " + format_job_sms(job, lang))
        return True
    if sub["channel"] == "telegram":
        from server.channels import telegram_bot

        return await telegram_bot.send_message(
            sub["address"], t(lang, "job_alert_prefix") + ":\n" + format_job(job, lang))
    return False


async def run_alerts() -> dict:
    """Send every subscriber the matching jobs they have not been sent yet."""
    jobs = load_jobs()
    with connect() as c:
        subs = [dict(r) for r in c.execute("SELECT * FROM subscriptions ORDER BY id")]
        already = {(r["subscription_id"], r["job_id"]) for r in c.execute("SELECT * FROM sent_alerts")}
    summary = {"subscriptions": len(subs), "sent": 0, "sms": 0, "telegram": 0, "failed": 0}
    for sub in subs:
        todo = [j for j in jobs if matches(j, sub["keyword"]) and (sub["id"], j["id"]) not in already]
        for job in todo[:MAX_PER_RUN]:
            if await _deliver(sub, job):
                with connect() as c:
                    c.execute(
                        "INSERT OR IGNORE INTO sent_alerts (subscription_id, job_id) VALUES (?,?)",
                        (sub["id"], job["id"]),
                    )
                summary["sent"] += 1
                summary[sub["channel"]] = summary.get(sub["channel"], 0) + 1
            else:  # e.g. Telegram bot not running: left unsent, retried next run
                summary["failed"] += 1
    return summary
