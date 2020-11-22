from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit, \
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QGridLayout, \
    QCheckBox, QComboBox, QGroupBox, QDateTimeEdit, QAction, QFileDialog, QTableWidget, \
    QTableWidgetItem
from PyQt5.QtCore import Qt, QDateTime, QRect
from PyQt5.QtGui import QIcon
import json
from kiwoom import Kiwoom
from wookutil import WookLog
from wookdata import *
import datetime, os

class TraderBase(QMainWindow, WookLog):
    def __init__(self, log, key):
        super().__init__()
        WookLog.custom_init(self, log)

        with open('setting.json') as r_file:
            self.setting = json.load(r_file)

        self.initUI()

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
        self.btn_add_item = QPushButton('Add')
        self.btn_add_item.clicked.connect(self.on_add_item)
        self.btn_remove_item = QPushButton('Remove')
        self.btn_remove_item.clicked.connect(self.on_remove_item)

        # Market information
        lb_martket_status = QLabel('Market status')
        self.lb_market_status = QLabel('no info')
        self.btn_get_item_info = QPushButton('Get item info')
        self.btn_get_item_info.clicked.connect(self.get_item_info)

        # Save Folder
        save_folder = self.setting['save_folder']
        if not os.path.exists(save_folder):
            os.mkdir(save_folder)
        today = datetime.date.today().strftime('%Y%m%d')
        self.log_file = save_folder + 'trader log ' + today + '.txt'
        lb_save_file = QLabel('Save')
        self.le_save_file = QLineEdit()
        self.le_save_file.setText(self.log_file)
        self.le_save_file.editingFinished.connect(self.on_edit_save_file)
        self.btn_change_file = QPushButton('Change')
        self.btn_change_file.clicked.connect(self.on_change_save_file)

        # Item grid layout
        item_grid = QGridLayout()
        item_grid.addWidget(lb_item_code, 0, 0)
        item_grid.addWidget(self.cbb_item_code, 0, 1)
        item_grid.addWidget(lb_item_name, 0, 2, 1, 2)
        item_grid.addWidget(self.cbb_item_name, 0, 4, 1, 2)
        item_grid.addWidget(self.btn_add_item, 0, 6, 1, 1)
        item_grid.addWidget(self.btn_remove_item, 0, 7, 1, 1)

        item_grid.addWidget(lb_martket_status, 1, 0, 1, 2)
        item_grid.addWidget(self.lb_market_status, 1, 2, 1, 3)
        item_grid.addWidget(self.btn_get_item_info, 1, 6, 1, 2)

        item_grid.addWidget(lb_save_file, 2, 0)
        item_grid.addWidget(self.le_save_file, 2, 1, 1, 6)
        item_grid.addWidget(self.btn_change_file, 2, 7)

        item_gbox = QGroupBox('Item information')
        item_gbox.setLayout(item_grid)

        # Go button
        self.btn_go = QPushButton('&Go')
        # self.btn_go.clicked.connect(self.get_stock_price)
        self.btn_go.setMaximumHeight(100)
        go_grid = QGridLayout()
        go_grid.addWidget(self.btn_go, 0, 0, 3, 1)

        # Portfolio table
        portfolio_header = ['item', 'purchase\nprice', 'evaluation', 'profit\nrate', 'amount']
        portfolio_header += ['current\nprice', 'purchase\nsum', 'evaluation\nsum', 'fee', 'tax']
        self.portfolio_table = QTableWidget(2, 10)
        self.portfolio_table.setHorizontalHeaderLabels(portfolio_header)
        self.portfolio_table.setRowHeight(0, 3)
        self.portfolio_table.setRowHeight(1, 5)
        self.portfolio_table.setRowHeight(2, 5)
        self.portfolio_table.setColumnWidth(0, 100)
        for column in range(1, self.portfolio_table.columnCount()):
            self.portfolio_table.setColumnWidth(column, 65)

        portfolio_gbox = QGroupBox('Portfolio')
        portfolio_grid = QGridLayout()
        portfolio_grid.addWidget(self.portfolio_table)
        portfolio_gbox.setLayout(portfolio_grid)

        # Trading table
        trading_header = ['item', 'transaction\ntime', 'current\nprice', 'ask\nprice', 'bid\nprice']
        trading_header += ['volume', 'accumul.\nvolume', 'highest\nprice', 'lowest\nprice', 'opening\nprice']
        self.trading_table = QTableWidget(4, 10)
        self.trading_table.setHorizontalHeaderLabels(trading_header)
        self.trading_table.setRowHeight(0, 3)
        self.trading_table.setRowHeight(1, 5)
        self.trading_table.setRowHeight(2, 5)
        self.trading_table.setColumnWidth(0, 100)
        for column in range(1, self.trading_table.columnCount()):
            self.trading_table.setColumnWidth(column, 65)

        trading_gbox = QGroupBox('Trading items')
        trading_grid = QGridLayout()
        trading_grid.addWidget(self.trading_table)
        trading_gbox.setLayout(trading_grid)

        # TextEdit
        self.te_info = QTextEdit()

        # Central Layout
        top_hbox = QHBoxLayout()
        top_hbox.addWidget(account_gbox)
        top_hbox.addWidget(item_gbox)
        top_hbox.addLayout(go_grid)
        top_hbox.addStretch()

        vbox = QVBoxLayout()
        vbox.addLayout(top_hbox)
        vbox.addWidget(portfolio_gbox)
        vbox.addWidget(trading_gbox)
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
        self.resize(800, 600)
        self.move(100, 100)
        self.setWindowIcon(QIcon('nyang1.ico'))
        self.show()