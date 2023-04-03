import httpx
import re
from datetime import datetime, timedelta
from icalendar import Calendar, Event
from pypdf import PdfReader


MENU_PAGE = "https://kokkarnir.is/maturinn/matsedill-fyrirtaekjathjonusta/"
# Kokkarnir.is blocks scrapers unless we pretend to be someone else:
USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"


def download_pdf_files(page):
    headers={
        "User-Agent": USER_AGENT
    }
    page_text = httpx.get(page, headers=headers).text

    # Get menu PDFs as tuples of (URL, filename):
    pdf_links = re.findall(r'(https://.*/(.*.pdf))', page_text)

    for menu in pdf_links:
        with open(menu[1], 'wb') as f:
            f.write(httpx.get(menu[0], headers=headers, timeout=20).content)

    return [pdf[1] for pdf in pdf_links]


def parse_menus(filenames):
    meat_menu = {"filename": "menu.ics"}
    vegan_menu = {"filename": "vegan_menu.ics"}
    monday = datetime.now() - timedelta(days=datetime.now().weekday())
    day_patterns = {
        monday.date(): r'(Mánudagur[\S\s]*)Þriðjudagur',
        (monday + timedelta(days=1)).date(): r'(Þriðjudagur[\S\s]*)Miðvikudagur',
        (monday + timedelta(days=2)).date(): r'(Miðvikudagur[\S\s]*)Fimmtudagur',
        (monday + timedelta(days=3)).date(): r'(Fimmtudagur[\S\s]*)Föstudagur',
        (monday + timedelta(days=4)).date(): r'(Föstudagur[\S\s]*)',
    }

    for filename in filenames:
        reader = PdfReader(filename)
        full_menu = reader.pages[0].extract_text()
        for date, pattern in day_patterns.items():
            if "vegan" in filename:
                vegan_menu[date] = re.search(pattern, full_menu).group(1)
            else:
                meat_menu[date] = re.search(pattern, full_menu).group(1)

    return (meat_menu, vegan_menu)


def generate_ics_files(menus):
    for menu in menus:
        calendar = Calendar()
        calendar.add('prodid', '-//Vikumatseðill mötuneytis Kokkanna//olisindri.com//')
        calendar.add('version', '2.0')
        
        for date, value in menu.items():
            if date == 'filename':
                continue
            split_menu = value.split('\n')
            cleaned = "\n".join([item.strip() for item in split_menu[1:] if item.strip()])
            menu[date] = cleaned
            start_time = datetime(date.year, date.month, date.day, 11, 0, 0)
            day_event = Event()
            day_event.add('summary', cleaned)
            day_event.add('description', cleaned)
            day_event.add('dtstart', start_time)
            day_event.add('dtend', start_time + timedelta(hours=2))
            day_event.add('dtstamp', start_time)
            day_event['uid'] = f'{start_time.isoformat()}/olisindri@gmail.com'

            calendar.add_component(day_event)
        
        with open(menu['filename'], 'wb') as ics_file:
            ics_file.write(calendar.to_ical())


filenames = download_pdf_files(MENU_PAGE)
generate_ics_files(parse_menus(filenames))
