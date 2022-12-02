import PySimpleGUI as sg
import requests
from bs4 import BeautifulSoup
import re
from pyperclip import copy, PyperclipException
import json
from os.path import isfile, dirname, realpath, join
from datetime import datetime

PAN_SEARCH_URL = 'https://ird.gov.np/pan-search'
PAN_FETCH_URL = 'https://ird.gov.np/statstics/getPanSearch'

output_file = "logs.json"

current_path = dirname(realpath(__file__))
# log_path = f'{current_path}\{output_file}'
log_path = join(current_path, output_file)

BUTTON_SIZE = 8

def create_file_if_not_exist(filename):
    if isfile(filename) is False:
        try:
            open(filename, 'a').close()
        except:
            print('Failed creating the file', filename)

def main_window():
    layout = [
            [sg.Text("PAN Number:", size=12, justification="r"), sg.Input(key="-IN-", size=16), sg.Button("Search", size=BUTTON_SIZE)],
            [sg.Push(), sg.Input(disabled=True, key='OUTPUT', size=28 , visible=True), sg.Btn("copy", size=BUTTON_SIZE, visible=True)],
            [sg.Push() , sg.Button("Reset", size=BUTTON_SIZE) , sg.Exit(size=BUTTON_SIZE, button_color="tomato")],
    ]

    window_title = "IRD PAN Search"
    window = sg.Window(window_title, layout, use_custom_titlebar=False, finalize=True)

    window['-IN-'].bind("<Return>", "Search")

    while True:
        # window['copy'].hide_row()
        event, values = window.read()
        print(event, values)
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        if event in ("Search", "-IN-Search"):
            if verify_input_type(values["-IN-"]):
                sg.popup_quick_message("Searching...")
                fetched_name = fetch_pan(pan_no=values["-IN-"])
                if not fetched_name == "INVALID":
                    window['OUTPUT'].update(value=fetched_name)
        if event == "Reset":
            window['-IN-'].update(value="")
            window['OUTPUT'].update(value="")

        if event == "copy":
            try:
                copy(window['OUTPUT'].Get())
            except PyperclipException as exception_msg:
                sg.popup_no_titlebar(exception_msg)
    window.close()

def verify_input_type(pan_input):
    """Verifies the input, a number or not"""
    if pan_input.isnumeric():
        return True
    if pan_input == "":
        sg.popup_no_titlebar("PAN number is required!")
        return False
    sg.popup_quick_message("Invalid PAN number!")
    return False


def fetch_pan(pan_no):
    session = requests.Session()
    session.headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-IN,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://www.google.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }
    response = session.get(PAN_SEARCH_URL)
    soup = BeautifulSoup(response.text, 'lxml')


    # Extracting token and captcha
    token = soup.form.input['value']
    script = soup.find('script', type = 'text/javascript').string
    captcha_value = re.search(r'var stotal="(.*?)"', script).group(1)

    data = {
        '_token': token,
        'pan': pan_no,
        'captcha': captcha_value,
    }

    res_result = session.post(PAN_FETCH_URL, data)
    
    if res_result.text == '0':
        sg.PopupOK("Invalid PAN!")
        return "INVALID"
    
    #  ----------------------------->> Debugging <<---------------------------------
    response_logs = []
    create_file_if_not_exist(log_path)
    with open(log_path, encoding="utf-8") as fp:
        try:
            response_logs = json.load(fp)
        except json.JSONDecodeError:
            pass
    
    log = dict()
    log["date"] = datetime.now().strftime("%m/%d - %H:%M:%S")
    log[pan_no] = res_result.json()
    response_logs.insert(0, log)

    with open(log_path, 'w', encoding="utf-8") as file:
        json.dump(response_logs, file, indent=2, ensure_ascii=False)
    
    #  ----------------------------->> Debugging End <<---------------------------------

    panDetails = res_result.json()['panDetails']
    
    name = panDetails[0]['trade_Name_Eng']
    print('Name:', " ".join(name.split()))
    name = " ".join(name.split())
    try:
        copy(name)
    except PyperclipException as exception_msg:
        print(exception_msg)
    return name

if __name__ == '__main__':
    # sg.theme_previewer()
    font_family = "monospace"
    font_size = 14
    sg.set_options(font=(font_family, font_size))
    sg.theme("Green")

    main_window()

    