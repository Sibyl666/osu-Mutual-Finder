import sys
import json
import requests
from bs4 import BeautifulSoup
from .PushButton import PushButton
from PySide2.QtWidgets import QWidget, QCheckBox, QApplication, QCheckBox, QGridLayout, QSpinBox, QLabel, QListWidget, QLineEdit, QComboBox
from PySide2.QtCore import Qt


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QGridLayout()
        self.layout.setColumnStretch(0, 1)
        self.countrywidget_items = []
        
        # Stuff
        self.addfriendcheckbox = QCheckBox("Add Friend")
        self.addfriendcheckbox.stateChanged.connect(self.addfriendcheck)

        self.startfrompage = QSpinBox()
        self.startfrompage.setMinimumWidth(250)
        self.startfrompage.setMinimum(0)
        self.startfrompage.setMaximum(200)

        self.pagelimit = QSpinBox()
        self.pagelimit.setMinimumWidth(250)
        self.pagelimit.setMinimum(0)
        self.pagelimit.setMaximum(200)

        self.blacklistwidget = QListWidget()
        self.blacklistwidget.itemDoubleClicked.connect(self.remove_from_config_blacklist)
        self.countrywidget = QListWidget()
        self.countrywidget.itemDoubleClicked.connect(self.remove_from_config_country)

        self.startpageapplybutton = PushButton("Apply")
        self.startpageapplybutton.pressed.connect(self.start_page_signal)
        self.pagelimitapplybutton = PushButton("Apply")
        self.pagelimitapplybutton.pressed.connect(self.page_limit_signal)

        self.addblacklist = QSpinBox()
        self.addblacklist.setMaximum(1000000000)

        # self.addcountry = QLineEdit()
        # self.addcountry.setPlaceholderText("Country Here"),
        self.countrybox = QComboBox()
        self.countrybox.activated.connect(self.addcountrybuttonsignal)

        self.addblacklistbutton = PushButton("Add To Blacklist")
        self.addblacklistbutton.pressed.connect(self.addblacklistbuttonsignal)
        self.addcountrybutton = PushButton("Add To Countries")
        self.addcountrybutton.pressed.connect(self.addcountrybuttonsignal)

        self.layout.addWidget(self.addfriendcheckbox, 0, 0)
        self.returnback_button = PushButton("Return Back")
        self.layout.addWidget(self.returnback_button, 0, 1, 1, 2)
        
        self.layout.addWidget(QLabel("Start From Page:"), 1, 0)
        self.layout.addWidget(self.startfrompage, 1, 0, Qt.AlignRight)
        self.layout.addWidget(self.startpageapplybutton, 1, 1, 1, 2)

        self.layout.addWidget(QLabel("Page Limit:"), 2, 0)
        self.layout.addWidget(self.pagelimit, 2, 0, Qt.AlignRight)
        self.layout.addWidget(self.pagelimitapplybutton, 2, 1, 1, 2)

        self.layout.addWidget(QLabel("Blacklist"), 3, 0)
        self.layout.addWidget(self.blacklistwidget, 4, 0)
        self.layout.addWidget(self.addblacklist, 5, 0)
        self.layout.addWidget(self.addblacklistbutton, 6, 0)

        self.layout.addWidget(QLabel("Country List"), 3, 1)
        self.layout.addWidget(self.countrywidget, 4, 1, 1, -1)
        self.layout.addWidget(self.countrybox, 5, 1, 1, 2)
        # self.layout.addWidget(self.addcountrybutton, 6, 1, 1, 2)

        resp = requests.get("https://osu.ppy.sh/rankings/osu/country")
        soup = BeautifulSoup(resp.content, "html.parser")
        self.json_country_data = json.loads(soup.find(id="json-countries").string)

        self.setLayout(self.layout)

    def get_config(self):
        try:
            with open("./config.json", "r", encoding="utf-8") as file:
                return json.loads(file.read())
        except:
            with open("./error.txt", "a", encoding="utf-8") as file:
                file.write("Cant read config file (settings) \n")

    def write_config(self, write_to: str, value):
        config = self.get_config()

        if type(config[write_to]) is list:
            if value not in config[write_to]:
                config[write_to].append(value)
        else:
            config[write_to] = value

        with open("./config.json", "w", encoding="utf-8") as file:
            file.write(
                json.dumps(config, indent=4)
            )

    def remove_config(self, remove_from, value):
        config = self.get_config()

        config[remove_from].remove(value)

        with open("./config.json", "w", encoding="utf-8") as file:
            file.write(
                json.dumps(config, indent=4)
            )

    def remove_from_config_blacklist(self, item):
        item = self.blacklistwidget.findItems(item.text(), Qt.MatchExactly)[0]
        row = self.blacklistwidget.row(item)
        self.blacklistwidget.takeItem(row)
        self.remove_config("blacklist", int(item.text()))

    def remove_from_config_country(self, item):
        if self.countrywidget.count() > 1:
            country_code = item.text().split("|")[0].strip()
            self.remove_config("country", country_code)

            item = self.countrywidget.findItems(item.text(), Qt.MatchExactly)[0]
            row = self.countrywidget.row(item)
            self.countrywidget.takeItem(row)
        
    def load_settings(self):
        config = self.get_config()
        if config["add_friend"]:
            self.addfriendcheckbox.setChecked(True)

        for country in config["country"]:
            for country_code in self.json_country_data:
                if country == country_code["code"]:
                    self.countrywidget.addItem(f"{country_code['code']} | {country_code['name']}")
                    self.countrywidget_items.append(f"{country_code['code']} | {country_code['name']}")

        for blacklist in config["blacklist"]:
            if blacklist == config["blacklist"][0]:
                continue
            
            self.blacklistwidget.addItem(str(blacklist))

        for country in self.json_country_data:
            self.countrybox.addItem(f"{country['code']} | {country['name']}")

        self.startfrompage.setValue(config["start_from_page"])
        self.pagelimit.setValue(config["page_limit"])

    def addfriendcheck(self):
        self.write_config("add_friend", self.addfriendcheckbox.isChecked())

    def addblacklistbuttonsignal(self):
        value = self.addblacklist.value()
        self.addblacklist.clear()
        self.blacklistwidget.addItem(str(value))
        self.write_config("blacklist", value)

    def addcountrybuttonsignal(self, index):
        country_text = self.countrybox.itemText(index)
        if not country_text in self.countrywidget_items:
            self.countrywidget.addItem(country_text)
            self.countrywidget_items.append(country_text)

        country_code = country_text.split("|")[0].strip()
        self.write_config("country", country_code)
        # value = self.addcountry.text()
        # self.addcountry.clear()
        # self.countrywidget.addItem(value)
        # self.write_config("country", value)

    def start_page_signal(self):
        value = self.startfrompage.value()
        self.write_config("start_from_page", value)

    def page_limit_signal(self):
        value = self.pagelimit.value()
        self.write_config("page_limit", value)

if __name__ == "__main__":
    app = QApplication([])
    form = SettingsWidget()
    form.show()
    sys.exit(app.exec_())
