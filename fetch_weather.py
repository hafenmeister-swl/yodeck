import requests
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
from html import escape
import re

SOURCE_URL = "https://www.ostsee-charter-yacht.de/aktueller-seewetterbericht.php"
OUTPUT = Path("seewetter.html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


# ============================================================
# DOWNLOAD
# ============================================================

response = requests.get(
    SOURCE_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

print("Downloaded:", SOURCE_URL)
print("HTTP status:", response.status_code)


# ============================================================
# PARSE
# ============================================================

soup = BeautifulSoup(response.text, "html.parser")

# Remove things we definitely don't want
for tag in soup([
    "script",
    "style",
    "noscript",
    "iframe",
    "form",
    "nav",
    "header",
    "footer",
    "button"
]):
    tag.decompose()


# ============================================================
# FIND TITLE
# ============================================================

h1 = soup.find("h1")

if not h1:
    raise RuntimeError("Could not find H1.")

title = h1.get_text(" ", strip=True)

print("Title:", title)


# ============================================================
# FIND TIMESTAMP
# ============================================================

timestamp = "Aktueller Bericht"

# Search the text following the H1
for text_node in h1.find_all_next(string=True):

    text = str(text_node).strip()

    if not text:
        continue

    match = re.search(
        r"(\d{1,2}\.\d{1,2}\.\d{4}\s*-\s*\d{1,2}:\d{2}\s*Uhr)",
        text
    )

    if match:
        timestamp = match.group(1)
        break

print("Timestamp:", timestamp)


# ============================================================
# FIND WEATHER SECTIONS
# ============================================================

headings = soup.find_all("h3")

print("Found headings:", len(headings))


sections = []

for heading in headings:

    heading_text = heading.get_text(" ", strip=True)

    if not heading_text:
        continue

    # Only keep actual weather sections
    if not any(word in heading_text.lower() for word in [
        "wetterlage",
        "vorhersage"
    ]):
        continue

    print("Processing section:", heading_text)

    texts = []

    # Walk through every text node after this heading
    # until the next h3.
    for node in heading.find_all_next(string=True):

        # Stop at the next section heading
        parent = node.parent

        if parent and parent.name == "h3":
            break

        text = str(node).strip()

        if not text:
            continue

        # Remove whitespace noise
        text = re.sub(r"\s+", " ", text).strip()

        # Ignore known website clutter
        lower = text.lower()

        if any(ignore in lower for ignore in [
            "bericht drucken",
            "gedruckt von",
            "für smartphone",
            "drucken",
            "quelle:",
            "die ostsee.de info gmbh"
        ]):
            continue

        texts.append(text)


    # Remove duplicates while preserving order
    unique_texts = []

    for text in texts:
        if text not in unique_texts:
            unique_texts.append(text)


    if unique_texts:

        sections.append({
            "title": heading_text,
            "texts": unique_texts
        })


# ============================================================
# CHECK
# ============================================================

if not sections:
    raise RuntimeError(
        "No weather content could be extracted."
    )


print("")
print("======================================")
print("WEATHER CONTENT FOUND")
print("======================================")

for section in sections:

    print("")
    print(section["title"])

    for text in section["texts"]:
        print("  >", text)


# ============================================================
# CREATE HTML
# ============================================================

section_html = []

for section in sections:

    content = []

    for text in section["texts"]:

        content.append(
            f'<p>{escape(text)}</p>'
        )

    section_html.append(
        f"""
        <section class="weather-section">

            <h2>{escape(section["title"])}</h2>

            {"".join(content)}

        </section>
        """
    )


report_html = "\n".join(section_html)


# ============================================================
# YODECK DISPLAY
# ============================================================

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

/* ==========================================================
   BASE
   ========================================================== */

* {{
    box-sizing: border-box;
}}

html,
body {{

    margin: 0;
    padding: 0;

    width: 100%;
    height: 100%;

}}

body {{

    background:
        linear-gradient(
            180deg,
            #031521 0%,
            #082a3d 50%,
            #03121d 100%
        );

    color: #f5f8fa;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    overflow: hidden;

}}


/* ==========================================================
   HEADER
   ========================================================== */

.header {{

    position: fixed;

    z-index: 100;

    top: 0;
    left: 0;
    right: 0;

    min-height: 135px;

    padding: 25px 55px;

    background:
        linear-gradient(
            180deg,
            rgba(2,16,27,0.99),
            rgba(2,16,27,0.93)
        );

    border-bottom:
        2px solid rgba(100,200,230,0.3);

    box-shadow:
        0 5px 25px rgba(0,0,0,0.45);

}}


/* ==========================================================
   TITLE
   ========================================================== */

.title {{

    margin: 0;

    font-size: 42px;

    line-height: 1.1;

    font-weight: 700;

    letter-spacing: 0.5px;

}}


.subtitle {{

    margin-top: 8px;

    font-size: 20px;

    color: #83d2e8;

}}


/* ==========================================================
   TIMESTAMP
   ========================================================== */

.timestamp {{

    position: absolute;

    right: 55px;
    top: 31px;

    padding: 13px 20px;

    border-radius: 8px;

    background:
        rgba(12,91,118,0.42);

    border:
        1px solid rgba(110,215,240,0.45);

    color: #c8f4fc;

    font-size: 23px;

    font-weight: 700;

    white-space: nowrap;

}}


/* ==========================================================
   VIEWPORT
   ========================================================== */

.viewport {{

    position: fixed;

    top: 135px;
    bottom: 0;

    left: 0;
    right: 0;

    overflow: hidden;

}}


/* ==========================================================
   SCROLLER
   ========================================================== */

.scroller {{

    animation:
        autoScroll 100s
        linear
        infinite;

}}


/* ==========================================================
   REPORT
   ========================================================== */

.report {{

    max-width: 1250px;

    margin: 0 auto;

    padding:
        45px 70px 350px;

}}


/* ==========================================================
   SECTIONS
   ========================================================== */

.weather-section {{

    margin-bottom: 45px;

}}


.weather-section h2 {{

    margin:
        0 0 20px;

    padding-bottom: 10px;

    border-bottom:
        2px solid rgba(100,205,230,0.3);

    color: #80d5ed;

    font-size: 33px;

    line-height: 1.2;

}}


.weather-section p {{

    margin:
        0 0 18px;

    color: #f3f7f9;

    font-size: 28px;

    line-height: 1.6;

}}


/* ==========================================================
   SOURCE
   ========================================================== */

.source {{

    margin-top: 45px;

    padding-top: 25px;

    border-top:
        1px solid rgba(110,190,215,0.25);

    color: #83a5b2;

    font-size: 17px;

    line-height: 1.5;

}}


/* ==========================================================
   AUTOMATIC SCROLL
   ========================================================== */

@keyframes autoScroll {{

    0% {{
        transform: translateY(0);
    }}

    8% {{
        transform: translateY(0);
    }}

    92% {{
        transform:
            translateY(
                calc(-100% + 650px)
            );
    }}

    100% {{
        transform: translateY(0);
    }}

}}


/* ==========================================================
   SMALLER SCREENS
   ========================================================== */

@media (max-width: 1100px) {{

    .header {{

        padding:
            20px 30px;

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

        margin-top: 10px;

        font-size: 18px;

    }}

    .viewport {{

        top: 175px;

    }}

    .report {{

        padding:
            35px 35px 250px;

    }}

    .weather-section h2 {{

        font-size: 27px;

    }}

    .weather-section p {{

        font-size: 22px;

    }}

}}


</style>

</head>


<body>


<header class="header">

    <div class="title">
        🌊 Seewetterbericht Ostsee
    </div>

    <div class="subtitle">
        Deutscher Wetterdienst · Seewetterdienst Hamburg
    </div>

    <div class="timestamp">
        {escape(timestamp)}
    </div>

</header>


<div class="viewport">

    <div class="scroller">

        <main class="report">

            {report_html}

            <div class="source">

                Quelle:
                Deutscher Wetterdienst,
                Seewetterdienst Hamburg

                <br><br>

                Automatisch aktualisiert über
                ostsee-charter-yacht.de

            </div>

        </main>

    </div>

</div>


</body>

</html>
"""


# ==========================================================
# WRITE FILE
# ==========================================================

OUTPUT.write_text(
    html,
    encoding="utf-8"
)

print("")
print("======================================")
print("SUCCESS")
print("======================================")
print("Created:", OUTPUT)
