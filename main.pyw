import requests
import json
import time
import webbrowser
from Modules.PushButton import PushButton
from bs4 import BeautifulSoup
from PySide2.QtWidgets import QApplication, QWidget, QStackedLayout, QFormLayout, QGridLayout, QPushButton, QLabel, \
    QLineEdit, QStyle, QListWidget, QListWidgetItem
from PySide2.QtCore import Qt, QRunnable, QThreadPool, QObject, Signal, Slot, QVariantAnimation, QAbstractAnimation
from PySide2.QtGui import QGuiApplication, QFontDatabase, QColor


class Communicate(QObject):
    checking_signal = Signal(int, int)
    AddToChecked = Signal(int)
    found_mutual_signal = Signal(int)


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

    def get_user_detail(self, user_id):
        user_page = requests.get(
            f"https://osu.ppy.sh/users/{user_id}").content

        soup = BeautifulSoup(user_page, "html.parser")
        details = json.loads(soup.find(id="json-user").string)

        return details

    def add_friend(self, user_id):
        time.sleep(5)
        new_friend_list = session.post(
            f"https://osu.ppy.sh/home/friends?target={user_id}", headers=headers)
        if new_friend_list.status_code == 200:
            return new_friend_list.json()
        elif new_friend_list.status_code == 429:
            time.sleep(10)

            new_friend_list = session.post(
                f"https://osu.ppy.sh/home/friends?target={user_id}", headers=headers)

            return new_friend_list.json()

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

    def run(self):  # Main Work here
        first_friend_list = self.get_first_friend_list()
        for country in self.configs['country']:
            for page_count in range(self.configs['start_from_page'], self.configs['page_limit'] + 1):
                country_url_page = requests.get(
                    f"https://osu.ppy.sh/rankings/osu/performance?country={country}&page={page_count}").content
                soup = BeautifulSoup(country_url_page, "html.parser")

                # users
                for user in soup.find_all(class_="ranking-page-table__user-link-text js-usercard"):
                    user_id = int(user['data-user-id'])
                    signals.checking_signal.emit(page_count,
                                                 user_id)  # Update checking label

                    if user_id in self.configs["blacklist"]:
                        continue

                    if user_id in first_friend_list:
                        continue

                    signals.AddToChecked.emit(user_id)  # Add to Checked
                    # friend list after edded
                    for friend in self.add_friend(user_id):
                        if user_id == friend["target_id"]:  # find the user in list
                            if str(friend['mutual']) == "True":  # Check if mutual

                                # If mutual add to mutuals list widget
                                signals.found_mutual_signal.emit(user_id)

                                with open("mutuals.txt", "a") as file:
                                    file.write(
                                        f"{user_id} - {self.get_user_detail(user_id)['username']} \n")

                                if not self.configs['add_friend']:
                                    session.delete(
                                        f"https://osu.ppy.sh/home/friends/{user_id}", headers=headers)
                                    break

                                break
                            else:
                                session.delete(
                                    f"https://osu.ppy.sh/home/friends/{user_id}", headers=headers)
                                break


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

        self.mutuals_to_check = QListWidget()
        self.mutuals_to_check.itemDoubleClicked.connect(
            self.RedirectToUserProfile)
        self.found_mutuals = QListWidget()
        self.checking_label = QLabel("Page: 1 | Checking: 123456")
        self.checking_label.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(QLabel("Checked list"), 0, 0)
        main_layout.addWidget(self.mutuals_to_check, 1, 0)
        main_layout.addWidget(QLabel("Found Mutuals"), 0, 1)
        main_layout.addWidget(self.found_mutuals, 1, 1)
        main_layout.addWidget(self.checking_label, 2, 0)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.layout.addWidget(main_widget)


    @Slot(int, int)
    def UpdateChecking(self, page_count, checking_id):
        self.checking_label.setText(
            f"Page {page_count} | Checking: {checking_id}")

    @Slot(int)
    def AddToFoundMutual(self, user_id):
        self.found_mutuals.addItem(str(user_id))

    @Slot(int)
    def AddToChecked(self, user_id):
        self.mutuals_to_check.addItem(str(user_id))

    def RedirectToUserProfile(self, item):
        webbrowser.open(f"https://osu.ppy.sh/users/{item.text()}")

    def get_token(self):
        page = session.get("https://osu.ppy.sh/home").content
        soup = BeautifulSoup(page, "html.parser")
        token = soup.find(name="meta", attrs={"name": "csrf-token"})["content"]

        return token

    def Login(self, **kwargs):
        print("Logging in")

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

    def update_headers(self):
        page = session.get("https://osu.ppy.sh/home/friends").content
        soup = BeautifulSoup(page, "html.parser")
        token_after_login = soup.find(
            name="meta", attrs={"name": "csrf-token"})["content"]

        headers['X-CSRF-Token'] = token_after_login

    def verifymail(self):
        self.update_headers()
        verify_key = self.verify_textbox.text()
        status = session.post("https://osu.ppy.sh/home/account/verify",
                              data={"verification_key": verify_key}, headers=headers).status_code

        if status == 200:
            self.layout.setCurrentIndex(2)

            # Start Checking
            worker = Worker(self.get_config())
            self.threadpool.start(worker)
        else:
            self.verify_error_label.setText(
                "Cant verify. Check if the key is correct.")

    def get_user_detail(self, user_id):
        user_page = requests.get(
            f"https://osu.ppy.sh/users/{user_id}").content

        soup = BeautifulSoup(user_page, "html.parser")
        details = json.loads(soup.find(id="json-user").string)

        return details

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
                            "blacklist": [],
                            "start_from_page": 1,
                            "page_limit": 200
                        }, indent=4
                    )
                )

        # Add yourself to blacklist
        with open("config.json", "r", encoding="utf-8") as file:
            configs = json.loads(file.read())

        configs["blacklist"].append(
            self.get_user_detail(self.username_textbox.text())["id"]
        )

        with open("config.json", "w", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    configs, indent=4
                )
            )

        return configs


if __name__ == '__main__':
    app = QApplication([])
    form = Form()
    form.show()
    app.exec_()
