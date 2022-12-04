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

VERSION = 'Version 1.0.1'

output_file = "logs.json"

current_path = dirname(realpath(__file__))
log_path = join(current_path, output_file)

BUTTON_SIZE = 8

def create_file_if_not_exist(filename):
    if isfile(filename) is False:
        try:
            open(filename, 'a').close()
        except:
            print('Failed creating the file', filename)


def connected_to_internet(url='http://www.google.com/', timeout=6):
    """To check the internet connection"""
    try:
        _ = requests.head(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        pass
    return False

def no_internet_window():
    layout = [
        [sg.Text("Internet connection not available!")],
        [sg.Push(), sg.Btn("Ok", size=BUTTON_SIZE)]
    ]

    window_title = "IRD PAN Search"
    window = sg.Window(window_title, layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Ok"):
            break
        window.close()
    raise SystemExit()

def main_window():
    layout = [
            [sg.Text("PAN Number:", size=12, justification="r"), sg.Input(key="-IN-", size=16), sg.Button("Search", size=BUTTON_SIZE)],
            [sg.Push(), sg.Input(disabled=True, key='OUTPUT', size=28 , visible=True), sg.Btn("copy", size=BUTTON_SIZE, visible=True)],
            [sg.Btn("ⓘ", pad=(20, 0)), sg.Push() , sg.Button("Reset", size=BUTTON_SIZE) , sg.Exit(size=BUTTON_SIZE, button_color="tomato")],
    ]

    window_title = "IRD PAN Search"
    window = sg.Window(window_title, layout, use_custom_titlebar=False, finalize=True)

    window['-IN-'].bind("<Return>", "Search")

    while True:
        event, values = window.read()
        print(event, values)
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        if event in ("Search", "-IN-Search"):
            # Removes whitespaces
            pan_no = values["-IN-"].strip()
            # Number verification
            if verify_input_type(pan_no):
                sg.popup_quick_message("Searching...")
                pan_details = fetch_pan_details(pan_no=pan_no)
                fetched_name = pan_details['trade_Name_Eng']
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
        
        if event == "ⓘ":
            window.disappear()
            sg.popup(VERSION, "Developed by Ashish Kandu", grab_anywhere=True, title="About")
            window.reappear()
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


def fetch_pan_details(pan_no):
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
    try:
        response = session.get(PAN_SEARCH_URL)
    except requests.exceptions.ConnectionError:
        sg.popup_no_titlebar("Please check your internet connection")
        raise SystemExit()
    except:
        sg.popup_no_titlebar("Something went wrong.")
        raise SystemExit()
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
    try:
        res_result = session.post(PAN_FETCH_URL, data)
    except requests.exceptions.ConnectionError:
        sg.popup_no_titlebar("Please check your internet connection")
        raise SystemExit()
    except:
        sg.PopupQuickMessage("Something went wrong.")
        raise SystemExit()
    
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
    try:
        panDetails = res_result.json()['panDetails'][0]
    except:
        sg.PopupNoTitlebar("Information not found in the response!")
        raise SystemExit()
    
    # ----------------------------->> Outputs <<---------------------------------
    fields = ('telephone', 'mobile', 'street_Name', 'vdc_Town')
    
    details = dict()
    details['pan'] = pan_no
    
    # name = " ".join(panDetails['trade_Name_Eng'].split())
    try:
        details['trade_Name_Eng'] = " ".join(panDetails['trade_Name_Eng'].split())
    except:
        details['trade_Name_Eng'] = "!Problem with Name!"
    
    for field in fields:
    # to check if the mentioned field goes missing
        try:
            details[field] = panDetails[field]
        except KeyError as e:
            details[e.args[0]] = 'None'
            continue

    try:
        copy(details['trade_Name_Eng'])
    except PyperclipException as exception_msg:
        print(exception_msg)
    return details

if __name__ == '__main__':
    font_family = "monospace"
    font_size = 14
    sg.set_options(font=(font_family, font_size))
    sg.theme("Green")
    if not connected_to_internet():
        no_internet_window()
    main_window()

    