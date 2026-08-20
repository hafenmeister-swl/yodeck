import requests
from bs4 import BeautifulSoup
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


# ------------------------------------------------------------
# Download source page
# ------------------------------------------------------------

response = requests.get(
    SOURCE_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

print("Downloaded:", SOURCE_URL)
print("HTTP status:", response.status_code)
print("Content length:", len(response.text))


# ------------------------------------------------------------
# Parse HTML
# ------------------------------------------------------------

soup = BeautifulSoup(response.text, "html.parser")


# Remove scripts, navigation, etc.
for tag in soup([
    "script",
    "style",
    "noscript",
    "iframe",
    "form",
    "nav",
    "header",
    "footer"
]):
    tag.decompose()


# ------------------------------------------------------------
# Find the report title
# ------------------------------------------------------------

title = soup.find("h1")

if not title:
    raise RuntimeError(
        "Could not find the Seewetterbericht heading."
    )

title_text = title.get_text(" ", strip=True)

print("Title:", title_text)


# ------------------------------------------------------------
# Find timestamp
# ------------------------------------------------------------

timestamp = None

# Look at text immediately following the H1
for element in title.find_all_next():

    text = element.get_text(" ", strip=True)

    if not text:
        continue

    match = re.search(
        r"(?:herausgegeben.*?am\s+)?"
        r"(\d{1,2}\.\d{1,2}\.\d{4}\s*-\s*\d{1,2}:\d{2}\s*Uhr)",
        text,
        re.IGNORECASE
    )

    if match:
        timestamp = match.group(1)
        break


if not timestamp:
    timestamp = "Aktueller Bericht"


print("Timestamp:", timestamp)


# ------------------------------------------------------------
# Extract report sections
# ------------------------------------------------------------

report = []

current_section = None

# Start reading after the H1
for element in title.find_all_next():

    if element.name in ["h2", "h3", "h4"]:

        text = element.get_text(" ", strip=True)

        if not text:
            continue

        # Stop at unrelated content
        if text.lower() in [
            "das aktuelle ostsee-wetter sehen sie hier",
            "mehr informationen"
        ]:
            break

        current_section = {
            "title": text,
            "content": []
        }

        report.append(current_section)

    elif element.name in ["p", "li"]:

        text = element.get_text(" ", strip=True)

        if not text:
            continue

        lower = text.lower()

        # Ignore website clutter
        if any(ignore in lower for ignore in [
            "gedruckt von",
            "bericht drucken",
            "für smartphone",
            "drucken",
            "ostsee.de info gmbh übernimmt"
        ]):
            continue

        if current_section:
            current_section["content"].append(text)


# ------------------------------------------------------------
# Check extraction
# ------------------------------------------------------------

if not report:
    raise RuntimeError(
        "No weather report sections could be extracted."
    )


print("Sections found:", len(report))

for section in report:
    print(
        " -",
        section["title"],
        ":",
        len(section["content"]),
        "paragraph(s)"
    )


# ------------------------------------------------------------
# Generate HTML
# ------------------------------------------------------------

sections_html = []

for section in report:

    paragraphs = []

    for text in section["content"]:

        paragraphs.append(
            f"<p>{escape(text)}</p>"
        )

    section_html = f"""
        <section class="weather-section">

            <h2>{escape(section["title"])}</h2>

            {"".join(paragraphs)}

        </section>
    """

    sections_html.append(section_html)


report_html = "\n".join(sections_html)


# ------------------------------------------------------------
# Generate Yodeck display
# ------------------------------------------------------------

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
            #041522 0%,
            #08283b 55%,
            #03111c 100%
        );

    color: #f4f8fa;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    overflow: hidden;
}}


/* ---------------------------------------------------------
   HEADER
   --------------------------------------------------------- */

.header {{

    position: fixed;

    z-index: 10;

    top: 0;
    left: 0;
    right: 0;

    min-height: 125px;

    padding: 24px 55px;

    background:
        linear-gradient(
            180deg,
            rgba(3,17,28,0.99),
            rgba(3,17,28,0.92)
        );

    border-bottom:
        2px solid rgba(100,190,220,0.25);

    box-shadow:
        0 5px 25px rgba(0,0,0,0.4);
}}


.title {{

    margin: 0;

    font-size: 42px;

    line-height: 1.1;

    font-weight: 700;

    letter-spacing: 0.5px;
}}


.subtitle {{

    margin-top: 7px;

    font-size: 20px;

    color: #85cfe5;
}}


.timestamp {{

    position: absolute;

    right: 55px;
    top: 30px;

    padding: 12px 20px;

    border-radius: 8px;

    border:
        1px solid rgba(100,210,235,0.45);

    background:
        rgba(20,95,120,0.4);

    color: #c5f3fc;

    font-size: 23px;

    font-weight: 700;

    white-space: nowrap;
}}


/* ---------------------------------------------------------
   SCROLLING AREA
   --------------------------------------------------------- */

.viewport {{

    position: fixed;

    top: 125px;
    bottom: 0;

    left: 0;
    right: 0;

    overflow: hidden;
}}


.scroller {{

    width: 100%;

    animation:
        autoScroll 110s
        linear
        infinite;
}}


.report {{

    max-width: 1250px;

    margin: 0 auto;

    padding:
        45px 70px 300px;
}}


/* ---------------------------------------------------------
   SECTIONS
   --------------------------------------------------------- */

.weather-section {{

    margin-bottom: 40px;
}}


.weather-section h2 {{

    margin: 0 0 18px;

    padding-bottom: 9px;

    border-bottom:
        2px solid rgba(110,205,230,0.3);

    color: #7fd4ed;

    font-size: 32px;

    line-height: 1.2;
}}


.weather-section p {{

    margin:
        0 0 20px;

    font-size: 28px;

    line-height: 1.6;

    color: #f3f7f9;
}}


/* ---------------------------------------------------------
   FOOTER
   --------------------------------------------------------- */

.source {{

    margin-top: 40px;

    padding-top: 25px;

    border-top:
        1px solid rgba(120,190,210,0.25);

    color: #88a8b5;

    font-size: 17px;

    line-height: 1.5;
}}


/* ---------------------------------------------------------
   AUTOMATIC SCROLL
   --------------------------------------------------------- */

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


/* ---------------------------------------------------------
   YODECK / SMALLER SCREEN
   --------------------------------------------------------- */

@media (max-width: 1100px) {{

    .header {{
        padding: 20px 30px;
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

    .weather-section p {{
        font-size: 22px;
    }}

    .weather-section h2 {{
        font-size: 27px;
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


# ------------------------------------------------------------
# Write output
# ------------------------------------------------------------

OUTPUT.write_text(
    html,
    encoding="utf-8"
)

print(
    "Successfully created:",
    OUTPUT
)
