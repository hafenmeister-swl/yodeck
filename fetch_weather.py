import requests
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
from html import escape
import re

SOURCE_URL = "https://www.ostsee-charter-yacht.de/aktueller-seewetterbericht.php"
OUTPUT = Path("seewetter.html")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
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


# Remove things we don't need
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
# TITLE
# ============================================================

h1 = soup.find("h1")

if not h1:
    raise RuntimeError("Could not find H1.")

title = h1.get_text(" ", strip=True)

print("Title:", title)


# ============================================================
# TIMESTAMP
# ============================================================

timestamp = "Aktueller Bericht"

page_text = soup.get_text(" ", strip=True)

match = re.search(
    r"herausgegeben.*?am\s+"
    r"(\d{1,2}\.\d{1,2}\.\d{4}\s*-\s*\d{1,2}:\d{2}\s*Uhr)",
    page_text,
    re.IGNORECASE
)

if match:
    timestamp = match.group(1)

print("Timestamp:", timestamp)


# ============================================================
# FIND WEATHER HEADINGS
# ============================================================

headings = soup.find_all("h3")

weather_headings = []

for heading in headings:

    text = heading.get_text(" ", strip=True)

    if any(word in text.lower() for word in [
        "wetterlage",
        "vorhersage"
    ]):
        weather_headings.append(heading)


print("Weather headings:", len(weather_headings))


if not weather_headings:
    raise RuntimeError(
        "Could not find weather headings."
    )


# ============================================================
# EXTRACT CONTENT BETWEEN HEADINGS
# ============================================================

sections = []


for index, heading in enumerate(weather_headings):

    heading_text = heading.get_text(
        " ",
        strip=True
    )

    print("Processing:", heading_text)

    # Find the next weather heading
    if index + 1 < len(weather_headings):
        next_heading = weather_headings[index + 1]
    else:
        next_heading = None

    texts = []

    # --------------------------------------------------------
    # Walk through elements after this heading
    # --------------------------------------------------------

    for element in heading.next_elements:

        # Stop at next weather heading
        if (
            next_heading is not None
            and element is next_heading
        ):
            break

        # Only process text nodes
        if not isinstance(element, NavigableString):
            continue

        text = str(element).strip()

        if not text:
            continue

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        if not text:
            continue

        lower = text.lower()

        # Ignore page/navigation noise
        if any(ignore in lower for ignore in [
            "bericht drucken",
            "gedruckt von",
            "für smartphone",
            "drucken",
            "quelle:",
            "seite empfehlen",
            "teilen"
        ]):
            continue

        texts.append(text)


    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    cleaned = []

    for text in texts:

        if text not in cleaned:
            cleaned.append(text)


    if cleaned:

        sections.append({
            "title": heading_text,
            "texts": cleaned
        })


# ============================================================
# DEBUG OUTPUT
# ============================================================

print("")
print("========================================")
print("EXTRACTED WEATHER REPORT")
print("========================================")

for section in sections:

    print("")
    print(section["title"])

    for text in section["texts"]:
        print("  >", text)


if not sections:

    raise RuntimeError(
        "No weather content could be extracted."
    )


# ============================================================
# BUILD REPORT HTML
# ============================================================

sections_html = []


for section in sections:

    content = []

    for text in section["texts"]:

        # Split very long text into readable paragraphs
        content.append(
            f'<p>{escape(text)}</p>'
        )


    sections_html.append(
        f"""
        <section class="weather-section">

            <h2>{escape(section["title"])}</h2>

            {"".join(content)}

        </section>
        """
    )


report_html = "\n".join(
    sections_html
)


# ============================================================
# GENERATE YODECK HTML
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

/* =========================================================
   BASE
   ========================================================= */

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
            #031522 0%,
            #082b3e 55%,
            #03121d 100%
        );

    color: #f5f8fa;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    overflow: hidden;

}}


/* =========================================================
   HEADER
   ========================================================= */

.header {{

    position: fixed;

    z-index: 100;

    top: 0;
    left: 0;
    right: 0;

    height: 140px;

    padding: 25px 55px;

    background:
        linear-gradient(
            180deg,
            rgba(2,16,27,0.99),
            rgba(2,16,27,0.94)
        );

    border-bottom:
        2px solid rgba(100,200,230,0.30);

    box-shadow:
        0 5px 25px rgba(0,0,0,0.45);

}}


/* =========================================================
   TITLE
   ========================================================= */

.title {{

    margin: 0;

    font-size: 42px;

    line-height: 1.1;

    font-weight: 700;

}}


.subtitle {{

    margin-top: 8px;

    font-size: 20px;

    color: #83d2e8;

}}


/* =========================================================
   TIMESTAMP
   ========================================================= */

.timestamp {{

    position: absolute;

    top: 32px;
    right: 55px;

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


/* =========================================================
   VIEWPORT
   ========================================================= */

.viewport {{

    position: fixed;

    top: 140px;
    bottom: 0;

    left: 0;
    right: 0;

    overflow: hidden;

}}


/* =========================================================
   SCROLLER
   ========================================================= */

.scroller {{

    animation:
        autoScroll 100s
        linear
        infinite;

}}


/* =========================================================
   REPORT
   ========================================================= */

.report {{

    max-width: 1250px;

    margin: 0 auto;

    padding:
        45px 70px 350px;

}}


/* =========================================================
   WEATHER SECTION
   ========================================================= */

.weather-section {{

    margin-bottom: 45px;

}}


.weather-section h2 {{

    margin:
        0 0 20px;

    padding-bottom: 10px;

    border-bottom:
        2px solid rgba(100,205,230,0.30);

    color: #80d5ed;

    font-size: 33px;

    line-height: 1.2;

}}


.weather-section p {{

    margin:
        0 0 20px;

    color: #f3f7f9;

    font-size: 28px;

    line-height: 1.6;

}}


/* =========================================================
   FOOTER
   ========================================================= */

.source {{

    margin-top: 50px;

    padding-top: 25px;

    border-top:
        1px solid rgba(110,190,215,0.25);

    color: #83a5b2;

    font-size: 17px;

    line-height: 1.5;

}}


/* =========================================================
   AUTOMATIC SCROLL
   ========================================================= */

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


/* =========================================================
   SMALLER DISPLAY
   ========================================================= */

@media (max-width: 1100px) {{

    .header {{

        height: 175px;

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


# ============================================================
# WRITE
# ============================================================

OUTPUT.write_text(
    html,
    encoding="utf-8"
)

print("")
print("========================================")
print("SUCCESS")
print("========================================")
print("Created:", OUTPUT)
