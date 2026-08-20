import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
from datetime import datetime, timezone

SOURCE_URL = "https://www.ostsee-charter-yacht.de/aktueller-seewetterbericht-drucken.php"
OUTPUT = Path("seewetter.html")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Seewetterbericht/1.0)"
}


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


response = requests.get(
    SOURCE_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# Remove scripts and anything related to printing/navigation
for tag in soup([
    "script",
    "style",
    "noscript",
    "iframe",
    "form",
    "button",
    "nav",
    "header",
    "footer"
]):
    tag.decompose()


# ------------------------------------------------------------
# Try to identify the main report content
# ------------------------------------------------------------

main = (
    soup.find("main")
    or soup.find("article")
    or soup.find(id=re.compile("content|main|weather|wetter", re.I))
)

if not main:
    main = soup.body

if not main:
    raise RuntimeError("Could not find page content.")


# ------------------------------------------------------------
# Extract useful text blocks
# ------------------------------------------------------------

blocks = []

for element in main.find_all([
    "h1",
    "h2",
    "h3",
    "h4",
    "p",
    "li",
    "dt",
    "dd"
]):

    text = clean_text(element.get_text(" ", strip=True))

    if not text:
        continue

    # Ignore website/navigation/printing clutter
    lower = text.lower()

    if any(x in lower for x in [
        "druckversion",
        "drucken",
        "print",
        "zurück",
        "home",
        "menü",
        "navigation",
        "gedruckt von"
    ]):
        continue

    blocks.append((element.name, text))


if not blocks:
    raise RuntimeError("No report content could be extracted.")


# ------------------------------------------------------------
# Detect timestamp
# ------------------------------------------------------------

timestamp = None

for _, text in blocks:

    if re.search(
        r"\b\d{1,2}[.:]\d{2}\s*(?:uhr)?\b",
        text,
        re.IGNORECASE
    ):
        timestamp = text
        break

if not timestamp:
    timestamp = "Aktueller Seewetterbericht"


# ------------------------------------------------------------
# Build report HTML
# ------------------------------------------------------------

report_html = []

for tag, text in blocks:

    escaped = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    if tag == "h1":
        report_html.append(
            f'<h2 class="section-title">{escaped}</h2>'
        )

    elif tag in ["h2", "h3", "h4"]:
        report_html.append(
            f'<h2 class="section-title">{escaped}</h2>'
        )

    else:
        report_html.append(
            f'<p>{escaped}</p>'
        )


report_html = "\n".join(report_html)


# ------------------------------------------------------------
# Generate page
# ------------------------------------------------------------

generated = datetime.now(timezone.utc).strftime(
    "%d.%m.%Y %H:%M UTC"
)


html = f"""<!DOCTYPE html>
<html lang="de">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    http-equiv="refresh"
    content="1800"
>

<title>Seewetterbericht Ostsee</title>


<style>

/* =========================================================
   YODECK / MARITIME DISPLAY
   ========================================================= */

html,
body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;

    background:
        linear-gradient(
            180deg,
            #061827 0%,
            #08283c 50%,
            #04131f 100%
        );

    color: #f2f7fa;

    font-family:
        Arial,
        Helvetica,
        sans-serif;
}}


body {{
    overflow: hidden;
}}


/* =========================================================
   HEADER
   ========================================================= */

.header {{

    position: fixed;

    top: 0;
    left: 0;
    right: 0;

    z-index: 100;

    padding: 28px 55px 24px;

    background:
        linear-gradient(
            180deg,
            rgba(4,18,30,0.98),
            rgba(4,18,30,0.90)
        );

    border-bottom:
        2px solid rgba(110,190,220,0.25);

    box-shadow:
        0 8px 30px rgba(0,0,0,0.35);
}}


.title {{

    font-size: 42px;

    font-weight: 700;

    letter-spacing: 1px;

    margin: 0;

    color: #ffffff;
}}


.subtitle {{

    margin-top: 8px;

    font-size: 21px;

    color: #8fd3e8;
}}


/* =========================================================
   TIMESTAMP
   ========================================================= */

.timestamp {{

    position: absolute;

    right: 55px;
    top: 30px;

    padding: 13px 20px;

    border-radius: 8px;

    background:
        rgba(20,92,119,0.35);

    border:
        1px solid rgba(120,210,235,0.35);

    color: #b9edf9;

    font-size: 22px;

    font-weight: 600;

    white-space: nowrap;
}}


/* =========================================================
   REPORT
   ========================================================= */

.viewport {{

    position: absolute;

    top: 125px;
    bottom: 0;

    left: 0;
    right: 0;

    overflow: hidden;
}}


.report {{

    max-width: 1200px;

    margin: 0 auto;

    padding:
        45px 70px 250px;

    font-size: 27px;

    line-height: 1.65;

    animation:
        scrollReport 100s
        linear
        infinite;
}}


.section-title {{

    margin-top: 38px;
    margin-bottom: 14px;

    padding-bottom: 8px;

    font-size: 31px;

    line-height: 1.25;

    color: #82d4ec;

    border-bottom:
        1px solid rgba(120,210,235,0.25);
}}


.report p {{

    margin:
        0 0 18px;

    color: #f1f5f7;
}}


/* =========================================================
   SOURCE
   ========================================================= */

.source {{

    max-width: 1200px;

    margin: 30px auto 0;

    padding: 25px 70px 80px;

    font-size: 17px;

    color: #7fa4b2;
}}


/* =========================================================
   AUTOMATIC SCROLL
   ========================================================= */

@keyframes scrollReport {{

    0% {{
        transform: translateY(0);
    }}

    8% {{
        transform: translateY(0);
    }}

    92% {{
        transform: translateY(
            calc(-100% + 850px)
        );
    }}

    100% {{
        transform: translateY(0);
    }}

}}


/* =========================================================
   SMALLER DISPLAYS
   ========================================================= */

@media (max-width: 1000px) {{

    .header {{
        padding: 22px 30px;
    }}

    .title {{
        font-size: 32px;
    }}

    .subtitle {{
        font-size: 17px;
    }}

    .timestamp {{
        position: static;

        display: inline-block;

        margin-top: 12px;

        font-size: 17px;
    }}

    .viewport {{
        top: 155px;
    }}

    .report {{
        padding:
            35px 35px 200px;

        font-size: 22px;
    }}

    .section-title {{
        font-size: 26px;
    }}

}}


</style>

</head>


<body>


<header class="header">

    <h1 class="title">
        🌊 Seewetterbericht Ostsee
    </h1>

    <div class="subtitle">
        Deutscher Wetterdienst · Seewetterdienst Hamburg
    </div>

    <div class="timestamp">
        {timestamp}
    </div>

</header>


<main class="viewport">

    <article class="report">

        {report_html}

        <div class="source">

            Quelle:
            Deutscher Wetterdienst,
            Seewetterdienst Hamburg

            <br><br>

            Aktualisiert:
            {generated}

        </div>

    </article>

</main>


</body>

</html>
"""


OUTPUT.parent.mkdir(parents=True, exist_ok=True)

OUTPUT.write_text(
    html,
    encoding="utf-8"
)

print(
    f"Seewetterbericht updated: {OUTPUT}"
)
