import requests
import json
import time
import webbrowser
import asyncio
import threading
import traceback
from aiohttp import ClientSession, TCPConnector
from Modules.PushButton import PushButton
from Modules.settings import SettingsWidget
from bs4 import BeautifulSoup
from PySide2.QtWidgets import QApplication, QWidget, QStackedLayout, QFormLayout, QGridLayout, QPushButton, QLabel, \
    QLineEdit, QStyle, QListWidget, QListWidgetItem
from PySide2.QtCore import Qt, QRunnable, QThreadPool, QObject, Signal, Slot, QVariantAnimation, QAbstractAnimation, QSize
from PySide2.QtGui import QGuiApplication, QFontDatabase, QColor, QPixmap, QIcon


class Communicate(QObject):
    checking_signal = Signal(int, int)
    AddToChecked = Signal(int, QIcon, str)
    found_mutual_signal = Signal(int, QIcon, str)
    update_config_signal = Signal()


signals = Communicate()
session = requests.Session()
headers = {
    'authority': 'osu.ppy.sh',
    'accept': '*/*;q=0.5, text/javascript, application/javascript, application/ecmascript, application/x-ecmascript',
    'x-requested-with': 'XMLHttpRequest',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://osu.ppy.sh',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://osu.ppy.sh/home',
    'accept-language': 'en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7',
}


class Worker(QRunnable):
    def __init__(self, configs):
        super(Worker, self).__init__()
        self.configs = configs
        self.first_friend_list = self.get_first_friend_list()

        signals.update_config_signal.connect(self.update_config)

    def get_first_friend_list(self):
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                friend_list_config = json.loads(file.read())["friends_json"]

            return [friend_id["target_id"] for friend_id in friend_list_config]
        except:
            resp = session.get("https://osu.ppy.sh/home/friends")
            soup = BeautifulSoup(resp.content, "html.parser")

            friends_json = json.loads(soup.find(id="json-users").string)

            return [friend_id["id"] for friend_id in friends_json]

    def add_friend(self, user_id):
        time.sleep(3)
        try:
            new_friend_list = session.post(
            f"https://osu.ppy.sh/home/friends?target={user_id}", headers=headers)
        except:
            with open("error.txt", "a") as file:
                file.write(f"Cant Add Friend exception {traceback.format_exc()} \n")

        if new_friend_list.status_code == 200:
            return new_friend_list.json()
        elif new_friend_list.status_code == 429:
            time.sleep(10)
            self.add_friend(user_id)
        else:
            with open("error.txt", "a") as file:
                file.write(f"Cant Add Friend {new_friend_list.status_code} \n")

    @Slot()
    def update_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                self.configs = json.loads(file.read())
        except Exception as err:
            with open("error.txt", "a") as file:
                file.write(f"Cant update config {err} \n")
            
    async def GetIconAndUsername(self, user_id):
        return await asyncio.gather(
            self.GetIcon(user_id),
            self.async_get_user_detail(user_id)
        )

    async def GetIcon(self, user_id):
        try:
            pixmap = QPixmap()
            url = f"https://a.ppy.sh/{user_id}"

            async with ClientSession(connector=TCPConnector(ssl=False)) as session:
                async with session.get(url) as response:
                    image_data = await response.read()

            pixmap.loadFromData(image_data)
            return QIcon(pixmap)
        except:
            with open("error.txt", "a") as file:
                file.write(f"Cant get icon exception {traceback.format_exc()} \n")

    async def async_get_user_detail(self, user_id):
        try:
            url = f"https://osu.ppy.sh/users/{user_id}"

            async with ClientSession(connector=TCPConnector(ssl=False)) as session:
                async with session.get(url) as response:
                    user_page = await response.read()

            soup = BeautifulSoup(user_page, "html.parser")
            details = json.loads(soup.find(id="json-user").string)

            return details["username"]
        except:
            with open("error.txt", "a") as file:
                file.write(f"Cant Add Friend exception {traceback.format_exc()} \n")

    def run(self):  # Main Work here
        for country in self.configs['country']:
            for page_count in range(self.configs['start_from_page'], self.configs['page_limit'] + 1):
                country_url_page = requests.get(
                    f"https://osu.ppy.sh/rankings/osu/performance?country={country}&page={page_count}").content
                soup = BeautifulSoup(country_url_page, "html.parser")

                # users
                for user in soup.find_all(class_="ranking-page-table__user-link-text js-usercard"):
                    user_id = int(user['data-user-id'])
                    
                    if user_id in self.configs["blacklist"]:
                        continue

                    if user_id in self.first_friend_list:
                        continue

                    signals.checking_signal.emit(page_count, user_id)  # Update checking label
                    icon, username = asyncio.run(self.GetIconAndUsername(user_id))
                    signals.AddToChecked.emit(user_id, icon, username)  # Add to Checked

                    # friend list after edded
                    friend_list_after_added = self.add_friend(user_id)

                    if friend_list_after_added is None:
                        with open("error.txt", "a") as file:
                            file.write(f"Cant add {user_id} returned None \n")
                        continue

                    for friend in self.add_friend(user_id):
                        if user_id == friend["target_id"]:  # find the user in list
                            if str(friend['mutual']) == "True":  # Check if mutual

                                # If mutual add to mutuals list widget
                                signals.found_mutual_signal.emit(user_id, icon, username)

                                with open("mutuals.txt", "a") as file:
                                    file.write(
                                        f"{user_id} - {username} \n")

                                if not self.configs['add_friend']:
                                    session.delete(
                                        f"https://osu.ppy.sh/home/friends/{user_id}", headers=headers)
                                    break

                            else:
                                session.delete(
                                    f"https://osu.ppy.sh/home/friends/{user_id}", headers=headers)


class Form(QWidget):
    def __init__(self):
        super(Form, self).__init__()
        self.setWindowTitle("OMTV2")
        with open("Stuff/style.stylesheet", "r") as file:
            self.setStyleSheet(file.read())
        self.setMinimumSize(700, 400)
        QFontDatabase.addApplicationFont("Stuff/Sen-Bold.ttf")
        self.threadpool = QThreadPool()

        self.layout = QStackedLayout()

        self.InitLoginPage()
        self.InitVerificationPage()
        self.InitMainPage()
        
        self.settingswidget = SettingsWidget()
        self.settingswidget.returnback_button.pressed.connect(self.return_back)
        self.layout.addWidget(self.settingswidget)

        self.setLayout(self.layout)

        # Signals
        signals.checking_signal.connect(self.UpdateChecking)
        signals.found_mutual_signal.connect(self.AddToFoundMutual)
        signals.AddToChecked.connect(self.AddToChecked)

        try:
            with open("config.json", "r") as file:
                config = json.loads(file.read())
            if config["username"] and config["password"]:
                self.Login(username=config["username"], password=config["password"])
        except:
            pass

    def return_back(self):
        self.layout.setCurrentIndex(2)
        signals.update_config_signal.emit()

    def center_window(self, widget):
        window = widget.window()
        window.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                window.size(),
                QGuiApplication.primaryScreen().availableGeometry(),
            ),
        )

    def InitLoginPage(self):  # Widget
        login_layout = QFormLayout()

        self.username_textbox = QLineEdit()
        self.username_textbox.setPlaceholderText("Username")
        self.password_textbox = QLineEdit()
        self.password_textbox.setEchoMode(QLineEdit.Password)
        self.password_textbox.setPlaceholderText("Password")
        self.login_button = PushButton("Login")

        self.login_button.pressed.connect(self.Login)
        login_layout.addRow(self.username_textbox)
        login_layout.addRow(self.password_textbox)
        login_layout.addRow(self.login_button)
        self.login_error_label = QLabel()
        login_layout.addRow(self.login_error_label)

        login_widget = QWidget()
        login_widget.setLayout(login_layout)
        self.layout.addWidget(login_widget)

    def InitVerificationPage(self):  # Widget
        verify_layout = QFormLayout()

        self.verify_textbox = QLineEdit()
        self.verify_textbox.setPlaceholderText("Verification Key")
        self.verify_button = PushButton("Verify")
        self.verify_button.pressed.connect(self.verifymail)
        verify_layout.addRow(self.verify_textbox)
        verify_layout.addRow(self.verify_button)
        self.verify_error_label = QLabel()
        verify_layout.addRow(self.verify_error_label)

        verif_widget = QWidget()
        verif_widget.setLayout(verify_layout)
        self.layout.addWidget(verif_widget)

    def InitMainPage(self):  # Widget
        main_layout = QGridLayout()
        main_layout.setRowStretch(1, 5)

        self.mutuals_to_check = QListWidget()
        self.mutuals_to_check.setIconSize(QSize(32, 32))
        self.mutuals_to_check.itemDoubleClicked.connect(
            self.RedirectToUserProfile)
        self.found_mutuals = QListWidget()
        self.found_mutuals.setIconSize(QSize(32, 32))
        self.found_mutuals.itemDoubleClicked.connect(self.RedirectToUserProfile)
        self.checking_label = QLabel("Page: 1 | Checking: 123456")
        self.checking_label.setAlignment(Qt.AlignCenter)

        self.settingsbutton = PushButton("Settings")
        self.settingsbutton.pressed.connect(self.OpenSettingsPage)
        
        main_layout.addWidget(QLabel("Checked list"), 0, 0)
        main_layout.addWidget(self.mutuals_to_check, 1, 0)
        main_layout.addWidget(QLabel("Found Mutuals"), 0, 1)
        main_layout.addWidget(self.found_mutuals, 1, 1)
        main_layout.addWidget(self.checking_label, 2, 0)
        main_layout.addWidget(self.settingsbutton, 3, 0, 1, 2)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.layout.addWidget(main_widget)

    def OpenSettingsPage(self):
        self.layout.setCurrentIndex(3)

    @Slot(int, int)
    def UpdateChecking(self, page_count, checking_id):
        self.checking_label.setText(
            f"Page {page_count} | Checking: {checking_id}")

    @Slot(int)
    def AddToFoundMutual(self, user_id, icon, username):
        list_widget_item = QListWidgetItem(username)
        list_widget_item.setIcon(icon)
        self.found_mutuals.addItem(list_widget_item)

    @Slot(int)
    def AddToChecked(self, user_id, icon, username):
        list_widget_item = QListWidgetItem(username)
        list_widget_item.setIcon(icon)
        self.mutuals_to_check.addItem(list_widget_item)

    def RedirectToUserProfile(self, item):
        webbrowser.open(f"https://osu.ppy.sh/users/{item.text()}")

    def get_token(self):
        page = session.get("https://osu.ppy.sh/home")
        if page.status_code == 200:
            soup = BeautifulSoup(page.content, "html.parser")
            token = soup.find(name="meta", attrs={"name": "csrf-token"})["content"]
            return token
        else:
            with open("error.txt", "a") as file:
                file.write(f"Cant Get token {page.status_code} \n")

    def Login(self, **kwargs):
        username = kwargs.get("username", self.username_textbox.text())
        password = kwargs.get("password", self.password_textbox.text())
        data = {
            '_token': self.get_token(),
            'username': username,
            'password': password
        }

        status = session.post('https://osu.ppy.sh/session',
                              headers=headers, data=data).status_code

        if status == 200:
            self.layout.setCurrentIndex(1)

            # Fire Verification
            # verification key should be send.
            session.get("https://osu.ppy.sh/home/account/edit")
        else:
            self.login_error_label.setText("Cant Login")
            with open("error.txt", "a") as file:
                file.write(f"Cant login {status} \n")

    def update_headers(self):
        page = session.get("https://osu.ppy.sh/home/friends")
        if page.status_code == 200:
            soup = BeautifulSoup(page.content, "html.parser")
            token_after_login = soup.find(
                name="meta", attrs={"name": "csrf-token"})["content"]

            headers['X-CSRF-Token'] = token_after_login
        else:
            with open("error.txt", "a") as file:
                file.write(f"Cant update headers {page.status_code} \n")

    def verifymail(self):
        self.update_headers()
        verify_key = self.verify_textbox.text()
        status = session.post("https://osu.ppy.sh/home/account/verify",
                              data={"verification_key": verify_key}, headers=headers).status_code

        if status == 200:
            self.layout.setCurrentIndex(2)

            # Start Checking
            worker = Worker(self.get_config())
            self.settingswidget.load_settings()
            self.threadpool.start(worker)
        else:
            self.verify_error_label.setText(
                "Cant verify. Check if the key is correct.")

            with open("error.txt", "a") as file:
                file.write(f"Cant verify {status} \n")

    def get_user_detail(self, user_id):
        user_page = requests.get(
            f"https://osu.ppy.sh/users/{user_id}")

        if user_page.status_code == 200:
            soup = BeautifulSoup(user_page.content, "html.parser")
            details = json.loads(soup.find(id="json-user").string)
            return details
        else:
            with open("error.txt", "a") as file:
                file.write(f"Cant get user detail {user_page.status_code} \n")

    def get_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                return json.loads(file.read())
        except:
            print("Generating new config file")
            with open("config.json", "w", encoding="utf-8") as file:
                file.write(
                    json.dumps(
                        {
                            "username": self.username_textbox.text(),
                            "password": self.password_textbox.text(),
                            "add_friend": False,
                            "country": ["TR"],
                            "blacklist": [self.get_user_detail(self.username_textbox.text())["id"]],
                            "start_from_page": 1,
                            "page_limit": 200
                        }, indent=4
                    )
                )
            with open("config.json", "r", encoding="utf-8") as file:
                configs = json.loads(file.read())

            return configs


if __name__ == '__main__':
    app = QApplication([])
    form = Form()
    form.show()
    app.exec_()
