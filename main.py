import httpx
import re
from datetime import datetime, timedelta
from icalendar import Calendar, Event
from pypdf import PdfReader
from spire.doc import Document
from spire.doc.common import FileFormat


MENU_PAGE = "https://kokkarnir.is/maturinn/matsedill-fyrirtaekjathjonusta/"
# Kokkarnir.is blocks scrapers unless we pretend to be someone else:
USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"


def download_files(page):
    headers={
        "User-Agent": USER_AGENT
    }
    page_text = httpx.get(page, headers=headers).text

    # Get menu files as tuples of (URL, filename):
    file_links = re.findall(r'(https://.*/(.*.(pdf|docx)))', page_text)

    for menu in file_links:
        with open(menu[1], 'wb') as f:
            f.write(httpx.get(menu[0], headers=headers, timeout=20).content)

    return [file[1] for file in file_links]


def parse_menus(filenames):
    meat_menu = {"filename": "menu.ics"}
    vegan_menu = {"filename": "vegan_menu.ics"}
    monday = datetime.now() - timedelta(days=datetime.now().weekday())
    day_patterns = {
        monday.date(): r'(M\s?á\s?n\s?u\s?d\s?a\s?g\s?u\s?r[\S\s]*)Þ\s?r\s?i\s?ð\s?j\s?u\s?d\s?a\s?g\s?u\s?r',
        (monday + timedelta(days=1)).date(): r'(Þ\s?r\s?i\s?ð\s?j\s?u\s?d\s?a\s?g\s?u\s?r[\S\s]*)M\s?i\s?ð\s?v\s?i\s?k\s?u\s?d\s?a\s?g\s?u\s?r',
        (monday + timedelta(days=2)).date(): r'(M\s?i\s?ð\s?v\s?i\s?k\s?u\s?d\s?a\s?g\s?u\s?r[\S\s]*)F\s?i\s?m\s?m\s?t\s?u\s?d\s?a\s?g\s?u\s?r',
        (monday + timedelta(days=3)).date(): r'(F\s?i\s?m\s?m\s?t\s?u\s?d\s?a\s?g\s?u\s?r[\S\s]*)F\s?ö\s?s\s?t\s?u\s?d\s?a\s?g\s?u\s?r',
        (monday + timedelta(days=4)).date(): r'(F\s?ö\s?s\s?t\s?u\s?d\s?a\s?g\s?u\s?r[\S\s]*)',
    }

    for filename in filenames:
        if "docx" in filename:
            word_doc = Document()
            word_doc.LoadFromFile(filename)
            filename = f"{filename}.pdf"
            word_doc.SaveToFile(filename, FileFormat.PDF)
            word_doc.Close()

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


filenames = download_files(MENU_PAGE)
generate_ics_files(parse_menus(filenames))
