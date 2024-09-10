import psutil
import os
import shutil
import sys
import httpx
import subprocess
import locale
import zipfile

import requests
import PySimpleGUI as sg
from archive import extract
import argparse

from settings import BACKEND_HOST

# Обработка аргументов командной строки
parser = argparse.ArgumentParser(description='Telegram Desktop multi-account.')
parser.add_argument('--dir', dest='directory',
                    help='Directory where TDeskmulti will store your Telegram accounts')
args = parser.parse_args()

# Определения директории, где будут храниться данные для
# мультииспользования аккаунтов в Telegram Desktop
if args.directory and os.path.isdir(args.directory):
    dir = os.path.realpath(args.directory) + '/.TDeskMulti/'
else:
    if (os.name == 'nt' and getattr(sys, 'frozen', False)):
        dir = os.getenv('APPDATA')+'/.TDeskMulti/'
    else:
        dir = os.path.dirname(os.path.realpath(__file__)) + '/.TDeskMulti/'

# Определение пути где будут храниться файлы портативной Telegram Desktop
if os.name == 'nt':
    telegram = dir+'bin/Telegram/Telegram.exe'
elif os.name == 'mac':
    print('MacOS is not supported.')
    quit()
else:
    telegram = dir+'bin/Telegram/Telegram'

process_name = telegram.split('/')[-1]

# Определение словаря для мультиязычности интерфейса
strings_en = {
    'update_accounts_list': 'Update Accounts List', 'update_tdesk': 'Update Telegram Desktop',
    'start_session': 'Start session', 'disconnect_session': 'Disconnect session',
    'enter_access_key': 'Enter access key', 'e_not_selected_account': 'Pls select an account',
    'e_account_exists': 'An account with this name already exists.',
    'error': 'Error', 'sure': 'Are you sure?', 'key_not_entered': 'Access key is not entered',
    'access_granted': 'Access granted', 'access_granted_message': 'Access granted for you',
    'access_denied': 'Access denied', 'try_again_message': 'Try again',
    'session_file_download_error': 'Session file download is failed', 'success_message': 'Success',
    'session_disconnected_successfully': 'Session disconnected successfully',
    'session_disconnection_is_failed': 'Session disconnection is failed',
    'session_still_running': 'Session is still running',
}
strings_uk = {
    'update_accounts_list': 'Оновити список акаунтів', 'update_tdesk': 'Оновити Telegram Desktop',
    'start_session': 'Запустити сесію', 'disconnect_session': 'Відключити сесію',
    'enter_access_key': 'Введіть код доступу', 'e_not_selected_account': 'Будь ласка, виберіть акаунт',
    'e_account_exists': 'Акаунт з цим імʼям вже існує', 'error': 'Помилка', 'sure': 'Ви впевнені?',
    'key_not_entered': 'Код доступу не введено', 'access_granted': 'Доступ надано',
    'access_granted_message': 'Доступ надано для вас', 'access_denied': 'Доступ не надано',
    'try_again_message': 'Доступ не надано для вас', 'session_file_download_error': 'Помилка завантаження файлу сесії',
    'session_disconnected_successfully': 'Сесія відключена успішно', 'success_message': 'Успіх',
    'session_disconnection_is_failed': 'Сесія не відключена',
    'session_still_running': 'Сесія ще активна',
}
strings_ru = {
    'update_accounts_list': 'Обновить список аккаунтов', 'update_tdesk': 'Обновить Telegram Desktop',
    'start_session': 'Запустить сессию', 'disconnect_session': 'Выключить сессию',
    'enter_access_key': 'Введите код доступа', 'e_not_selected_account': 'Пожалуйста, выберите аккаунт',
    'e_account_exists': 'Аккаунт с этим именем уже существует', 'error': 'Ошибка', 'sure': 'Вы уверены?',
    'key_not_entered': 'Код доступа не введен', 'access_granted': 'Доступ предоставлен',
    'access_granted_message': 'Доступ для вас предоставлен', 'access_denied': 'Доступ не предоставлен',
    'try_again_message': 'Доступ не предоставлен для вас',
    'session_file_download_error': 'Ошибка загружка файла сессии', 'success_message': 'Успех',
    'session_disconnected_successfully': 'Сессия успешно отключена',
    'session_disconnection_is_failed': 'Сессия не отключена', 'session_still_running': 'Сессия еще активна',
}
if locale.getdefaultlocale()[0] == 'uk_UA':
    strings = strings_uk
elif locale.getdefaultlocale()[0] == 'ru_RU':
    strings = strings_ru
else:
    strings = strings_en

# Выбор темы для приложения
sg.theme('SystemDefault')

# Запуск Telegram Desktop со скаченной папкой сессиии
def start_session(session_account):
    global telegram
    global process_name
    account_dir = os.path.join(dir, 'account')
    has_running_process = False
    old_account = None
    for file in os.listdir(account_dir):
        if file.endswith('.xyz'):
            old_account = file.split('.')[0]
            break
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Перевірка чи назва процесу збігається
            if proc.info['name'] == process_name:
                has_running_process = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if has_running_process or old_account:
        running_result = disconnect_session(old_account)
        if not running_result:
            sg.Popup(strings['error'],
                 strings['session_still_running'], icon=icon, font="None 12")
    with httpx.Client() as client:
        session_file_response = client.post(
            url=f'{BACKEND_HOST}telegram/session/get_session_folder',
            json={'session_name': session_account},
            timeout=20,
        )
        session_file_content = session_file_response.content
    if session_file_content:
        zip_path = os.path.join(account_dir, 'tdata.zip')
        with open(zip_path, 'wb') as zip_file:
            zip_file.write(session_file_content)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(account_dir)
            os.remove(zip_path)
        except zipfile.BadZipFile:
            sg.Popup(strings['error'],
                     strings['session_file_download_error'], icon=icon, font="None 12")
        account_file_path = os.path.join(account_dir, f'{session_account}.xyz')
        with open(account_file_path, 'w') as account_file:
            account_file.write('')
        subprocess.Popen([telegram, '-workdir', account_dir])
    else:
        sg.Popup(strings['error'],
                 strings['session_file_download_error'], icon=icon, font="None 12")

# Запуск Telegram Desktop со скаченной папкой сессиии
def disconnect_session(account=None, show_popup=True):
    global process_name
    account_dir = os.path.join(dir, 'account')
    if not account:
        for file in os.listdir(account_dir):
            if file.endswith('.xyz'):
                account = file.split('.')[0]
                break

    stop_process_result = kill_process_by_name(process_name)
    if not stop_process_result:
        if show_popup:
            sg.Popup(strings['error'], font="None 12")

    if os.path.exists(account_dir):
        # Проходимо по всім елементам в папці
        for filename in os.listdir(account_dir):
            file_path = os.path.join(account_dir, filename)
            try:
                # Якщо це файл або символічне посилання, видаляємо його
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                # Якщо це директорія, видаляємо її та весь вміст
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Помилка при видаленні {file_path}. Причина: {e}')
    else:
        print('Вказана папка не існує')
    if not account:
        return True
    with httpx.Client() as client:
        enable_session_response = client.post(
            url=f'{BACKEND_HOST}telegram/session/enable_session',
            json={'session_name': account},
            timeout=20,
        )
        enable_session = enable_session_response.json().get('status', '')
    if enable_session == 'ok':
        if show_popup:
            sg.Popup(strings['success_message'],
                     strings['session_disconnected_successfully'], icon=icon, font="None 12")
        return True
    else:
        if show_popup:
            sg.Popup(strings['error'],
                     strings['session_disconnection_is_failed'], icon=icon, font="None 12")
        return False


def kill_process_by_name(proc_name):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Перевірка чи назва процесу збігається
            if proc.info['name'] == proc_name:
                print(f"Знайдено процес: {proc.info['name']} (PID: {proc.info['pid']})")
                # Завершуємо процес
                proc.kill()
                print(f"Процес {proc.info['name']} завершено")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    return True


# Загрузка портативной версии Telegram Desktop
def download_tdesk():
    global dir
    global icon
    layout = [[sg.Combo(['Telegram Desktop', 'Telegram Desktop Alpha'], readonly=True, default_value='Telegram Desktop', font="None 12")],
              [sg.OK(font="None 12")]]
    window = sg.Window('Telegram Desktop version', icon=icon).Layout(layout)
    event, number = window.Read()
    version = number[0]
    window.Close()
    if version == None:
        return 'exit'
    file_name = ''
    link = ''
    if version == 'Telegram Desktop':
        if os.name == 'nt':
            link = 'https://telegram.org/dl/desktop/win_portable'
            file_name = dir+'telegram.zip'
        else:
            link = 'https://telegram.org/dl/desktop/linux'
            file_name = dir+'telegram.tar.xz'
    if version == 'Telegram Desktop Alpha':
        if os.name == 'nt':
            link = 'https://telegram.org/dl/desktop/win_portable?beta=1'
            file_name = dir+'telegram.zip'
        else:
            link = 'https://telegram.org/dl/desktop/linux?beta=1'
            file_name = dir+'telegram.tar.xz'
    if not file_name or not link:
        return 'exit'
    layout = [[sg.Text('Downloading Telegram Desktop...')],
              [sg.ProgressBar(100, orientation='h', size=(20, 20), key='progressbar')]]
    window = sg.Window('Downloading Telegram Desktop...',
                       icon=icon).Layout(layout)
    progress_bar = window.FindElement('progressbar')
    window.Read(timeout=0)
    with open(file_name, 'wb') as f:
        response = requests.get(link, stream=True)
        total_length = response.headers.get('content-length')
        if total_length is None:
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                percentage = int(100 * dl / total_length)
                progress_bar.UpdateBar(percentage)
                window.Read(timeout=0)
    extract(file_name, dir+'bin/', method='insecure')
    os.remove(file_name)
    window.Close()


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('')
    return os.path.join(base_path, relative_path)


def get_sessions_list():
    with httpx.Client() as client:
        accounts_response = client.get(f'{BACKEND_HOST}telegram/session/list')
        accounts = accounts_response.json()
    header = ["Session", "First Name", "Last Name", "Username", "Phone", "Active"]
    rows = [
        [
            account.get('session', ''), account.get('first_name', ''), account.get('last_name', ''),
            account.get('username', ''), account.get('phone', ''), '',
        ] for account in accounts
    ]
    return header, rows

if not os.path.exists(dir):
    os.makedirs(dir)
if not os.path.exists(dir+'account'):
    os.makedirs(dir+'account')
if not os.path.exists(dir+'bin'):
    os.makedirs(dir+'bin')
icon = resource_path('icon.ico')
if not os.path.exists(icon) or os.name == 'posix':
    icon = b'R0lGODlhIAAgAOfFAB6WyB6WyR+XyR+XyiCYyiCYyyGYyyGZyyGZzCKZzCKazCKazSOazSObzSObziSbzimayyScziSczyWczyWdzyWd0Cad0Cae0Cae0See0Sef0Sef0iif0iig0iig0ymg0zOezimh0ymh1Cqh1Cqi1Tmezzaf0Cui1Tmfzzmf0Cuj1iyj1jqg0Syk1zih0i2k1y2k2DSj1Duh0i2l2C6l2C6l2S6m2S+m2S+m2i+n2jCn2jCn202gzDCo20ei0DGo2zGo3DGp3DKp3DKp3TKq3TOq3TOq3lOizTSr3jSr30im1TSs3zWs4DWt4Dat4Teu4mGo0U6u3Waq01uu2mir0V+x3XGu1G2x2XWv1XOw1nWx1Ha23XS75Iq52YS/4ou+34u+4I6+3ZO93ITB5pbB35LC4pnB3pzB3ZPF5Z/H4qjI3azL36PN6qzL46zM5K3M5LDM4K3N5a3N5rHN4K3O56/O5a7R6rfR4rLS6bjR5rjV6r7U57bX7cja6sXb68rb68vc68Xe8Mje7szd7Mze7Mze7czf7szf787f7s/f7c/g783i8c/j8tTj79bk8NLm9Njm8dnm8dbn89jq9t3p8+Ds9eHs9eLt9uDu+OXu9eHv+eXv9+bw+Obx+ejx+Orx+Ofy+ery+Onz+enz+uvz+Ov0+uv1++31++32++72++72/O73/O/3/PD3/PH3/PD4/PH4/PL4/fL5/fP5/fT5/fT6/fX6/fb6/fj6/Pb7/ff7/fj7/vj8/vn8/vr8/vr9/vv9/vz+/v3+//7+//7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////yH5BAEKAP8ALAAAAAAgACAAAAj+AP8JHEhQ4JODCA8WXMhwIBMnCSMibNjQSJIlTJo4gSgxIUWCQ4gYsZiEyUOOHZ98/LcDCJAhQ0YmKXkypcqGN3Do2PEDiJAhRYwguZhxY0eGMGjUsIEjx44eQIKElEnTaMSCKla0eDGDho0bTqG+jEnSpNWJA0mcyLq161edPH0CFUpUI8eBH0SMUMv2RdKlTZ9GDcllzEyzEAVy6PAhhF6+Wrl6BbsjCptJrDRRNSsQg4YNHDzk3bs2clcvgUyxWv3oZ9ChS/5RqGABQwbQoh+vnWIH02pRlVbzgSpVpMUHESZQsHAhg4bFH2KUWbRqtSpKjlKtRhPWJcwiDBr+IJcw+wKGK3o6rV7NKVGk9a+qvN3ZUwgCBQsaOIhgIo2k9audAkkflLDSyiuwgOKXUkyFRcABByigQANhoAIgK5cM0oclrcASyyy0MNKXW2AJQAABBhyQgAI+kCHIKKU00scfm8Aiyyy12JILHpC1pRQAAQgwAAEFHHDfAiDk0QcgntyYYy679PKFXmBs0RcMAGQJgAAmPhihGH0Q4oott+gSpS+/KMHYIXSQltU/WmbJ5YkGQNHHHHeQwksvvwATTCiebWCIHKORIFCcWgY55B5wqKGFH8AIMwwxitCGgSFxhJbXoYjGKcAZa1ABoRm4FFPMG6amauonHQzUaZxTPBzRpQFSZFJMFiWgkAIidbAggwsEvdqpogRAYMWRDRTiBnkVFCTsq3N6qQAhbYjH0LPQztoFFgpQhO2rxBaw0rfCCrASp+TGeW6w6a7bkLDnBgQAOw=='

disconnect_session(show_popup=False)

layout = [
    [sg.Text(strings['enter_access_key'], font="None 12 bold")],
    [sg.Input(key='access_key', font="None 12")],
    [sg.Button('Enter', bind_return_key=True, font="None 12"), sg.Button('Cancel', font="None 12")]
]

window = sg.Window(title=strings['enter_access_key'], size=(250, 100), layout=layout)

while True:
    event, values = window.read()

    # Якщо користувач натискає 'Cancel' або закриває вікно
    if event == sg.WINDOW_CLOSED or event == 'Cancel':
        sg.Popup(strings['error'], strings['key_not_entered'], font="None 12")
        sys.exit(0)  # Завершити програму

    # Якщо натиснуто кнопку 'Enter' або клавішу Enter
    if event == 'Enter':
        access_key = values['access_key']

        if access_key:
            with httpx.Client() as client:
                access_response = client.post(
                    url=f'{BACKEND_HOST}telegram/session/check_access_key',
                    json={'access_key': access_key},
                    timeout=20,
                )
                access = access_response.json()

            has_access = access.get('has_access', False)

            if has_access:
                sg.Popup(strings['access_granted'], strings['access_granted_message'], font="None 12")
                break  # Виходимо з циклу, якщо доступ отримано
            else:
                sg.Popup(strings['access_denied'], strings['try_again_message'], font="None 12")
        else:
            sg.Popup(strings['error'], strings['key_not_entered'], font="None 12")

window.close()

if not os.path.exists(telegram):
    if download_tdesk() == 'exit':
        sys.exit(0)
header, rows = get_sessions_list()
layout = [
    [sg.Button(strings['update_accounts_list'], font="None 12 bold"), sg.Button(strings['update_tdesk'], font="None 12 bold")],
    [
        sg.Table(headings=header, values=rows, size=(50, 20), bind_return_key=True, key='selected_account', font='None 13'),
        sg.Column([[sg.Button(strings['start_session'], font="None 12 bold")], [sg.Button(strings['disconnect_session'], font="None 12 bold")], [sg.Exit(font="None 12 bold")]])
    ]
]
window = sg.Window('Telegram sessions switcher', icon=icon).Layout(layout)
while True:
    event, values = window.read()
    if event in (sg.WIN_CLOSED, "Exit"):
        result = disconnect_session()
        if not result:
            sg.Popup(strings['error'],
                     strings['session_still_running'], icon=icon, font="None 12")
        else:
            window.close()
            break
    if event == strings['update_accounts_list']:
        header, rows = get_sessions_list()
        window['selected_account'].update(values=rows)
    if event == strings['update_tdesk']:
        download_tdesk()
    if event == strings['start_session']:
        if values['selected_account'] == []:
            sg.Popup(strings['error'],
                     strings['e_not_selected_account'], icon=icon, font="None 12")
        else:
           start_session(rows[values['selected_account'][0]][0])
    if event == strings['disconnect_session']:
        if values['selected_account'] == []:
            sg.Popup(strings['error'],
                strings['e_not_selected_account'], icon=icon, font="None 12")
        else:
            if sg.PopupYesNo(strings['sure'], icon=icon, font="None 12") == 'Yes':
                disconnect_session(rows[values['selected_account'][0]][0])

window.Close()
