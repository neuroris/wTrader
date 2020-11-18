from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit, \
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QGridLayout, \
    QCheckBox, QComboBox, QGroupBox, QDateTimeEdit, QAction, QFileDialog
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QIcon
import json
from kiwoom import Kiwoom
from wookutil import WookLog
from wookdata import *

class TraderBase(QMainWindow, WookLog):
    def __init__(self, log, key):
        super().__init__()
        WookLog.custom_init(self, log)

        with open('setting.json') as r_file:
            self.setting = json.load(r_file)

        self.kiwoom = Kiwoom(log, key)
        self.initUI()
        self.initKiwoom()

    def initKiwoom(self):
        self.kiwoom.signal = self.on_kiwoom_signal
        self.kiwoom.status = self.on_kiwoom_status
        self.kiwoom.item_code = self.cbb_item_code.currentText()
        self.kiwoom.item_name = self.cbb_item_name.currentText()
        self.kiwoom.first_day = self.dte_first_day.text()
        self.kiwoom.last_day = self.dte_last_day.text()
        self.kiwoom.save_folder = self.le_save_folder.text()
        self.kiwoom.tick_type = self.cbb_tick.currentText()
        self.kiwoom.min_type = self.cbb_min.currentText()
        self.kiwoom.day_type = self.cbb_day.currentText()

    def initUI(self):
        # Test Button
        self.btn_test = QPushButton('Test')
        self.btn_test.clicked.connect(self.test)

        # Account information
        self.cb_auto_login = QCheckBox('Auto')
        self.cb_auto_login.setChecked(True)
        self.btn_login = QPushButton('Login', self)
        self.btn_login.clicked.connect(self.on_connect_kiwoom)
        lb_account = QLabel('Account')
        self.cbb_account = QComboBox()
        self.cbb_account.currentTextChanged.connect(self.on_select_account)

        account_grid = QGridLayout()
        account_grid.addWidget(self.cb_auto_login, 0, 0)
        account_grid.addWidget(self.btn_login, 0, 1)
        account_grid.addWidget(lb_account, 1, 0)
        account_grid.addWidget(self.cbb_account, 1, 1, 1, 2)
        account_grid.setColumnMinimumWidth(2, 10)

        account_gbox = QGroupBox('Account Information')
        account_gbox.setLayout(account_grid)

        # Item infomation
        lb_item_code = QLabel('Code')
        lb_item_name = QLabel('Name')
        self.cbb_item_code = QComboBox()
        self.cbb_item_name = QComboBox()
        self.cbb_item_code.setEditable(True)
        self.cbb_item_name.setEditable(True)
        self.cbb_item_code.currentTextChanged.connect(self.on_select_item_code)
        self.cbb_item_name.currentTextChanged.connect(self.on_select_item_name)
        self.cbb_item_code.addItem(CODE_KODEX_LEVERAGE)
        self.cbb_item_code.addItem(CODE_KODEX_INVERSE_2X)
        self.cbb_item_name.addItem(NAME_KODEX_LEVERAGE)
        self.cbb_item_name.addItem(NAME_KODEX_INVERSE_2X)

        # Period
        current_date = QDateTime.currentDateTime()
        lb_period = QLabel('Period')
        self.dte_first_day = QDateTimeEdit()
        self.dte_first_day.setCalendarPopup(True)
        self.dte_first_day.setDisplayFormat('yyyy-MM-dd')
        self.dte_first_day.setDateTime(current_date)
        lb_wave = QLabel('~')
        self.le_last_day = QLineEdit()
        self.dte_last_day = QDateTimeEdit()
        self.dte_last_day.setCalendarPopup(True)
        self.dte_last_day.setDisplayFormat('yyyy-MM-dd')
        self.dte_last_day.setDateTime(current_date)
        self.cb_one_day = QCheckBox('1-day')
        self.cb_one_day.setChecked(self.setting['one_day'])

        self.dte_first_day.dateChanged.connect(self.on_change_first_day)
        self.dte_last_day.dateChanged.connect(self.on_change_last_day)

        # Save Folder
        lb_save_folder = QLabel('Save')
        self.le_save_folder = QLineEdit()
        self.le_save_folder.setText(self.setting['save_folder'])
        self.le_save_folder.editingFinished.connect(self.on_edit_save_folder)
        self.btn_change_folder = QPushButton('Change')
        self.btn_change_folder.clicked.connect(self.on_change_save_folder)

        # Item grid layout
        item_grid = QGridLayout()
        item_grid.addWidget(lb_item_code, 0, 0)
        item_grid.addWidget(self.cbb_item_code, 0, 1)
        item_grid.addWidget(lb_item_name, 0, 2, 1, 2)
        item_grid.addWidget(self.cbb_item_name, 0, 4, 1, 2)

        item_grid.addWidget(lb_period, 1, 0)
        item_grid.addWidget(self.dte_first_day, 1, 1, 1, 2)
        item_grid.addWidget(lb_wave, 1, 3, Qt.AlignCenter)
        item_grid.addWidget(self.dte_last_day, 1, 4, 1, 1)
        item_grid.addWidget(self.cb_one_day, 1, 5)

        item_grid.addWidget(lb_save_folder, 2, 0)
        item_grid.addWidget(self.le_save_folder, 2, 1, 1, 4)
        item_grid.addWidget(self.btn_change_folder, 2, 5)

        item_gbox = QGroupBox('Item information')
        item_gbox.setLayout(item_grid)

        # Data type selection
        self.rb_tick = QRadioButton('Tick')
        self.rb_min = QRadioButton('Min')
        self.rb_day = QRadioButton('Day')
        self.cbb_tick = QComboBox()
        self.cbb_min = QComboBox()
        self.cbb_day = QComboBox()
        # self.rb_min.setChecked(True)
        # self.rb_tick.setChecked(True)
        self.rb_day.setChecked(True)

        self.cbb_tick.addItem(TICK_1)
        self.cbb_tick.addItem(TICK_3)
        self.cbb_tick.addItem(TICK_5)
        self.cbb_tick.addItem(TICK_10)
        self.cbb_tick.addItem(TICK_30)

        self.cbb_min.addItem(MIN_1)
        self.cbb_min.addItem(MIN_3)
        self.cbb_min.addItem(MIN_5)
        self.cbb_min.addItem(MIN_10)
        self.cbb_min.addItem(MIN_15)
        self.cbb_min.addItem(MIN_30)
        self.cbb_min.addItem(MIN_60)

        self.cbb_day.addItem(DAY_DATA)
        self.cbb_day.addItem(WEEK_DATA)
        self.cbb_day.addItem(MONTH_DATA)
        self.cbb_day.addItem(YEAR_DATA)

        self.cbb_tick.activated.connect(self.on_change_tick)
        self.cbb_min.activated.connect(self.on_change_min)
        self.cbb_day.activated.connect(self.on_change_day)

        data_type_grid = QGridLayout()
        data_type_grid.addWidget(self.rb_tick, 0, 0)
        data_type_grid.addWidget(self.cbb_tick, 0, 1)
        data_type_grid.addWidget(self.rb_min, 1, 0)
        data_type_grid.addWidget(self.cbb_min, 1, 1)
        data_type_grid.addWidget(self.rb_day, 2, 0)
        data_type_grid.addWidget(self.cbb_day, 2, 1)

        data_type_gbox = QGroupBox('Data Type')
        data_type_gbox.setLayout(data_type_grid)

        # Go button
        self.btn_go = QPushButton('&Go')
        self.btn_go.clicked.connect(self.get_stock_price)
        self.btn_go.setMaximumHeight(100)
        go_grid = QGridLayout()
        go_grid.addWidget(self.btn_go, 0, 0, 3, 1)

        # TextEdit
        self.te_info = QTextEdit()

        # Central Layout
        top_hbox = QHBoxLayout()
        top_hbox.addWidget(account_gbox)
        top_hbox.addWidget(item_gbox)
        top_hbox.addWidget(data_type_gbox)
        top_hbox.addLayout(go_grid)
        top_hbox.addStretch()

        vbox = QVBoxLayout()
        vbox.addLayout(top_hbox)
        vbox.addWidget(self.te_info)
        vbox.addWidget(self.btn_test)

        # Central widget
        cw = QWidget()
        cw.setLayout(vbox)

        # Menu bar
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet('background:rgb(140,230,255)')
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(exit_action)

        setting_action = QAction('Setting', self)
        setting_action.triggered.connect(self.edit_setting)
        edit_menu = menu_bar.addMenu('&Edit')
        edit_menu.addAction(setting_action)

        # Window setting
        self.setCentralWidget(cw)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('ready')
        self.setWindowTitle('wook\'s algorithm trader')
        self.resize(700, 600)
        self.move(300, 150)
        self.setWindowIcon(QIcon('nyang1.ico'))
        self.show()

    def edit_setting(self):
        self.debug('setting')

    def on_kiwoom_signal(self, *args):
        message = ''
        for arg in args:
            message += str(arg) + ' '

        self.te_info.append(message)

    def on_kiwoom_status(self, message):
        self.status_bar.showMessage(message)

    def on_select_account(self, account):
        self.kiwoom.account_number = int(account)

    def on_select_item_code(self, code):
        self.kiwoom.item_code = int(code)
        if code == CODE_KODEX_LEVERAGE:
            self.cbb_item_name.setCurrentText(NAME_KODEX_LEVERAGE)
        elif code == CODE_KODEX_INVERSE_2X:
            self.cbb_item_name.setCurrentText(NAME_KODEX_INVERSE_2X)
        else:
            self.cbb_item_name.setCurrentText('')

    def on_select_item_name(self, name):
        self.kiwoom.item_name = name
        if name == NAME_KODEX_LEVERAGE:
            self.cbb_item_code.setCurrentText(CODE_KODEX_LEVERAGE)
        elif name == NAME_KODEX_INVERSE_2X:
            self.cbb_item_code.setCurrentText(CODE_KODEX_INVERSE_2X)
        else:
            self.cbb_item_code.setCurrentText('')

    def on_change_first_day(self, date):
        self.kiwoom.first_day = date.toString('yyyy-MM-dd')
        if self.cb_one_day.isChecked():
            self.dte_last_day.setDate(date)

    def on_change_last_day(self, date):
        self.kiwoom.last_day = date.toString('yyyy-MM-dd')
        if self.cb_one_day.isChecked():
            self.dte_first_day.setDate(date)

    def on_edit_save_folder(self):
        folder = self.le_save_folder.text()
        self.kiwoom.save_folder = folder

    def on_change_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select folder', self.le_save_folder.text())
        if folder != '':
            self.le_save_folder.setText(folder)
            self.kiwoom.save_folder = folder

    def on_change_tick(self, index):
        self.rb_tick.setChecked(True)
        self.kiwoom.tick_type = self.cbb_tick.itemText(index)

    def on_change_min(self, index):
        self.rb_min.setChecked(True)
        self.kiwoom.min_type = self.cbb_min.itemText(index)

    def on_change_day(self, index):
        self.rb_day.setChecked(True)
        self.kiwoom.day_type = self.cbb_day.itemText(index)