from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit, \
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QGridLayout, \
    QCheckBox, QComboBox, QGroupBox, QDateTimeEdit, QAction, QFileDialog, QTableWidget, \
    QTableWidgetItem
from PyQt5.QtCore import Qt, QDateTime, QRect
from PyQt5.QtGui import QIcon, QBrush
import json
from wookutil import WookLog, WookUtil
from wookdata import *
import datetime, os

class TraderBase(QMainWindow, WookLog, WookUtil):
    def __init__(self, log):
        super().__init__()
        WookLog.custom_init(self, log)
        WookUtil.__init__(self)
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
        self.btn_login.clicked.connect(self.connect_kiwoom)
        lb_account = QLabel('Account')
        self.cbb_account = QComboBox()
        self.cbb_account.currentTextChanged.connect(self.on_select_account)
        lb_deposit = QLabel('Deposit')
        self.lb_deposit = QLabel('no info')

        account_grid = QGridLayout()
        account_grid.addWidget(self.cb_auto_login, 0, 0)
        account_grid.addWidget(self.btn_login, 0, 1)
        account_grid.addWidget(lb_account, 1, 0)
        account_grid.addWidget(self.cbb_account, 1, 1, 1, 2)
        account_grid.addWidget(lb_deposit, 2, 0)
        account_grid.addWidget(self.lb_deposit, 2, 1, 1, 2)
        # account_grid.setColumnMinimumWidth(2, 10)

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

        # Order
        lb_price = QLabel('Price')
        self.le_price = QLineEdit()
        self.le_price.setMaximumWidth(95)
        lb_amount = QLabel('Amount')
        self.le_amount = QLineEdit()
        self.le_amount.setMaximumWidth(80)
        self.rb_buy = QRadioButton('Buy')
        self.rb_sell = QRadioButton('Sell')
        self.rb_buy.setChecked(True)
        self.cbb_order_type = QComboBox()
        self.cbb_order_type.setMinimumHeight(32)
        self.cbb_order_type.setEditable(True)
        self.cbb_order_type.lineEdit().setReadOnly(True)
        self.cbb_order_type.lineEdit().setAlignment(Qt.AlignCenter)
        self.cbb_order_type.addItems(ORDER_TYPE)
        self.btn_order = QPushButton('Order')

        # Order information
        lb_orderable = QLabel('Orderable')
        self.lb_orderable = QLabel()
        lb_buyable = QLabel('Buyable')
        self.lb_buyable = QLabel()
        lb_sellable = QLabel('Sellable')
        self.lb_sellable = QLabel()

        # Item grid layout
        item_grid = QGridLayout()
        item_grid.addWidget(lb_item_code, 0, 0)
        item_grid.addWidget(self.cbb_item_code, 0, 1)
        item_grid.addWidget(lb_item_name, 0, 2)
        item_grid.addWidget(self.cbb_item_name, 0, 3, 1, 4)
        item_grid.addWidget(self.btn_add_item, 0, 7)
        item_grid.addWidget(self.btn_remove_item, 0, 8)

        item_grid.addWidget(lb_price, 1, 0)
        item_grid.addWidget(self.le_price, 1, 1)
        item_grid.addWidget(lb_amount, 1, 2, 1, 2)
        item_grid.addWidget(self.le_amount, 1, 4)
        item_grid.addWidget(self.rb_buy, 1, 5)
        item_grid.addWidget(self.rb_sell, 1, 6)
        item_grid.addWidget(self.cbb_order_type, 1, 7)
        item_grid.addWidget(self.btn_order, 1, 8)

        # item_grid.addWidget(lb_orderable, 2, 0)
        # item_grid.addWidget(self.lb_orderable, 2, 1)
        # item_grid.addWidget(lb_buyable, 2, 2)
        # item_grid.addWidget(self.lb_buyable, 2, 3)
        # item_grid.addWidget(lb_sellable, 2, 4)
        # item_grid.addWidget(self.lb_sellable, 2, 5)

        item_gbox = QGroupBox('Item information')
        item_gbox.setLayout(item_grid)

        # Go button
        self.btn_go = QPushButton('&Go')
        self.btn_go.clicked.connect(self.go)
        self.btn_go.setMaximumHeight(120)
        go_grid = QGridLayout()
        go_grid.addWidget(self.btn_go, 0, 0, 3, 1)

        # Portfolio table
        portfolio_header = ['item', 'purchase\nprice', 'profit', 'profit\nrate', 'purchase\namount']
        portfolio_header += ['current\nprice', 'purchase\nsum', 'evaluation\nsum', 'fee', 'tax']
        self.table_portfolio = QTableWidget(2, 10)
        self.table_portfolio.setHorizontalHeaderLabels(portfolio_header)
        for column in range(self.table_portfolio.columnCount()):
            header_item = self.table_portfolio.horizontalHeaderItem(column)

        self.table_portfolio.setRowHeight(0, 3)
        self.table_portfolio.setRowHeight(1, 5)
        self.table_portfolio.setRowHeight(2, 5)
        for column in range(1, self.table_portfolio.columnCount()):
            self.table_portfolio.setColumnWidth(column, 100)
        self.table_portfolio.setColumnWidth(0, 215)
        self.table_portfolio.setColumnWidth(6, 110)
        self.table_portfolio.setColumnWidth(7, 110)

        portfolio_gbox = QGroupBox('Portfolio')
        portfolio_grid = QGridLayout()
        portfolio_grid.addWidget(self.table_portfolio)
        portfolio_gbox.setLayout(portfolio_grid)

        # Trading table
        trading_header = ['item', 'transaction\ntime', 'current\nprice', 'ask\nprice', 'bid\nprice']
        trading_header += ['volume', 'accumulated\nvolume', 'highest\nprice', 'lowest\nprice', 'opening\nprice']
        self.table_trading = QTableWidget(2, 10)
        self.table_trading.setHorizontalHeaderLabels(trading_header)
        self.table_trading.setRowHeight(0, 3)
        self.table_trading.setRowHeight(1, 5)
        self.table_trading.setRowHeight(2, 5)
        for column in range(1, self.table_trading.columnCount()):
            self.table_trading.setColumnWidth(column, 100)
        self.table_trading.setColumnWidth(0, 215)
        self.table_trading.setColumnWidth(6, 120)

        trading_gbox = QGroupBox('Trading items')
        trading_grid = QGridLayout()
        trading_grid.addWidget(self.table_trading)
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
        self.resize(1250, 1000)
        self.move(100, 100)
        self.setWindowIcon(QIcon('nyang1.ico'))
        self.show()