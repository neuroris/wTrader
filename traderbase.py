from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QLineEdit, \
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QGridLayout, \
    QCheckBox, QComboBox, QGroupBox, QDateTimeEdit, QAction, QFileDialog, QTableWidget, \
    QTableWidgetItem, QSpinBox, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QDateTime, QRect
from PyQt5.QtGui import QIcon, QBrush
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import json
from wookutil import WookLog, WookUtil
from wookdata import *
import datetime, os

class WookSingal:
    def __init__(self):
        self.slot = None

    def connect(self, slot):
        self.slot = slot

    def emit(self, *args):
        self.slot(*args)

class WookImageScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.dropped = WookSingal()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        text = mimeData.text()
        file_name = text[8:]
        self.dropped.emit(file_name)

class TraderBase(QMainWindow, WookLog, WookUtil):
    def __init__(self, log):
        super().__init__()
        WookLog.custom_init(self, log)
        WookUtil.__init__(self)
        with open('setting.json') as r_file:
            self.setting = json.load(r_file)
        self.initUI()

    def initUI(self):
        ###### Account
        self.cb_auto_login = QCheckBox('Auto')
        self.cb_auto_login.setChecked(True)
        self.btn_login = QPushButton('Login', self)
        self.btn_login.clicked.connect(self.connect_kiwoom)
        lb_account = QLabel('Account')
        self.cbb_account = QComboBox()
        self.cbb_account.currentTextChanged.connect(self.on_select_account)
        lb_deposit = QLabel('Deposit')
        self.lb_deposit = QLabel('No info')
        self.lb_deposit.setStyleSheet('font-weight:bold; color:brown')
        lb_orderable = QLabel('Orderable')
        self.lb_orderable = QLabel('No info')
        self.lb_orderable.setStyleSheet('font-weight:bold; color:olive')

        account_grid = QGridLayout()
        account_grid.addWidget(self.cb_auto_login, 0, 0)
        account_grid.addWidget(self.btn_login, 0, 1)
        account_grid.addWidget(lb_account, 1, 0)
        account_grid.addWidget(self.cbb_account, 1, 1)
        account_grid.addWidget(lb_deposit, 2, 0)
        account_grid.addWidget(self.lb_deposit, 2, 1)
        account_grid.addWidget(lb_orderable, 3, 0)
        account_grid.addWidget(self.lb_orderable, 3, 1)
        account_gbox = QGroupBox('Account')
        account_gbox.setLayout(account_grid)

        ##### Manual Order
        # Order Parameters
        lb_price = QLabel('Price')
        self.sb_price = QSpinBox()
        self.sb_price.setGroupSeparatorShown(True)
        self.sb_price.setMinimumHeight(30)
        self.sb_price.setRange(0, 9000000)
        self.sb_price.setSingleStep(5)
        lb_amount = QLabel('Amount')
        self.sb_amount = QSpinBox()
        self.sb_amount.setGroupSeparatorShown(True)
        self.sb_amount.setMinimumHeight(30)
        self.sb_amount.setRange(0, 9000000)
        self.cbb_order_position = QComboBox()
        self.cbb_order_position.addItems(ORDER_POSITION_DICT)
        self.cbb_order_position.setMinimumHeight(32)
        self.cbb_order_position.setEditable(True)
        self.cbb_order_position.lineEdit().setReadOnly(True)
        self.cbb_order_position.lineEdit().setAlignment(Qt.AlignCenter)
        self.cbb_order_type = QComboBox()
        self.cbb_order_type.setMinimumHeight(32)
        self.cbb_order_type.setEditable(True)
        self.cbb_order_type.lineEdit().setReadOnly(True)
        self.cbb_order_type.lineEdit().setAlignment(Qt.AlignCenter)
        self.cbb_order_type.addItems(ORDER_TYPE)
        self.btn_order = QPushButton('Order')
        self.btn_order.setStyleSheet('font-weight:bold; background-color:peru')
        self.btn_order.clicked.connect(self.send_order)

        # Item information
        lb_item_code = QLabel('Code')
        lb_item_name = QLabel('Name')
        self.cbb_item_code = QComboBox()
        self.cbb_item_name = QComboBox()
        self.cbb_item_code.setEditable(True)
        self.cbb_item_name.setEditable(True)
        self.cbb_item_code.editTextChanged.connect(self.on_select_item_code)
        self.cbb_item_name.currentIndexChanged.connect(self.on_select_item_name)
        self.cbb_item_code.addItems(CODES)
        self.cbb_item_name.addItems(CODES.values())
        self.btn_add_item = QPushButton('Add')
        self.btn_add_item.clicked.connect(self.on_add_item)
        self.btn_remove_item = QPushButton('Remove')
        self.btn_remove_item.clicked.connect(self.on_remove_item)
        self.btn_remove_item.setMinimumWidth(150)

        # Order Correction
        lb_order_number = QLabel('Order Number')
        self.le_order_number = QLineEdit()
        self.le_order_number.setMaximumWidth(80)

        order_number_hbox = QHBoxLayout()
        order_number_hbox.addWidget(lb_order_number)
        order_number_hbox.addWidget(self.le_order_number)

        # Tradable Parameters
        lb_buyable = QLabel('Buyable')
        self.lb_buyable = QLabel()
        self.lb_buyable.setStyleSheet('font-weight:bold; color:indigo')
        lb_sellable = QLabel('Sellable')
        self.lb_sellable = QLabel()
        self.lb_sellable.setStyleSheet('font-weight:bold; color:purple')

        tradeable_hbox = QHBoxLayout()
        tradeable_hbox.addWidget(lb_buyable)
        tradeable_hbox.addWidget(self.lb_buyable)
        tradeable_hbox.addWidget(lb_sellable)
        tradeable_hbox.addWidget(self.lb_sellable)

        # Chart
        self.btn_go_chart = QPushButton('Go Chart')
        self.btn_go_chart.clicked.connect(self.go_chart)
        self.btn_stop_chart = QPushButton('Stop Chart')
        self.btn_stop_chart.clicked.connect(self.stop_chart)

        # Test
        self.le_test = QLineEdit()
        self.le_test.setMaximumWidth(150)
        self.btn_test1 = QPushButton('Test1')
        self.btn_test1.clicked.connect(self.test1)
        self.btn_test1.setMaximumWidth(70)
        self.btn_test2 = QPushButton('Test2')
        self.btn_test2.clicked.connect(self.test2)

        # Manual Check
        self.btn_deposit = QPushButton('Deposit')
        self.btn_deposit.clicked.connect(self.get_deposit)
        self.btn_portfolio = QPushButton('Portfolio')
        self.btn_portfolio.clicked.connect(self.get_portfolio)
        self.btn_order_history = QPushButton('Order history')
        self.btn_order_history.clicked.connect(self.get_order_history)

        # Order grid layout
        order_grid = QGridLayout()
        order_grid.addWidget(lb_item_code, 0, 0)
        order_grid.addWidget(self.cbb_item_code, 0, 1)
        order_grid.addWidget(lb_item_name, 0, 2)
        order_grid.addWidget(self.cbb_item_name, 0, 3, 1, 3)
        order_grid.addWidget(self.btn_add_item, 0, 6)
        order_grid.addWidget(self.btn_remove_item, 0, 7)
        order_grid.addWidget(lb_price, 1, 0)
        order_grid.addWidget(self.sb_price, 1, 1)
        order_grid.addWidget(lb_amount, 1, 2, 1, 2)
        order_grid.addWidget(self.sb_amount, 1, 4)
        order_grid.addWidget(self.cbb_order_position, 1, 5)
        order_grid.addWidget(self.cbb_order_type, 1, 6)
        order_grid.addWidget(self.btn_order, 1, 7)
        order_grid.addLayout(order_number_hbox, 2, 0, 1, 3)
        order_grid.addLayout(tradeable_hbox, 2, 3, 1, 3)
        order_grid.addWidget(self.btn_go_chart, 2, 6)
        order_grid.addWidget(self.btn_stop_chart, 2, 7)
        order_grid.addWidget(self.le_test, 3, 0, 1, 2)
        order_grid.addWidget(self.btn_test1, 3, 2, 1, 2)
        order_grid.addWidget(self.btn_test2, 3, 4, 1, 1)
        order_grid.addWidget(self.btn_deposit, 3, 5)
        order_grid.addWidget(self.btn_portfolio, 3, 6)
        order_grid.addWidget(self.btn_order_history, 3, 7)
        order_gbox = QGroupBox('Manual Order')
        order_gbox.setLayout(order_grid)

        ##### Portfolio table
        portfolio_header = ['Item', 'Current\nPrice', 'Purchase\nPrice', 'Holding\nAmount', 'Purchase\nSum']
        portfolio_header += ['Evaluation\nSum', 'Fee', 'Tax', 'Profit', 'Profit\nRate']
        self.table_portfolio = QTableWidget(0, 10)
        self.table_portfolio.cellClicked.connect(self.on_select_portfolio_table)
        self.table_portfolio.setHorizontalHeaderLabels(portfolio_header)
        for column in range(1, self.table_portfolio.columnCount()):
            self.table_portfolio.setColumnWidth(column, 100)
        self.table_portfolio.setColumnWidth(0, 215)
        self.table_portfolio.setColumnWidth(4, 110)
        self.table_portfolio.setColumnWidth(5, 110)

        portfolio_gbox = QGroupBox('Portfolio')
        portfolio_grid = QGridLayout()
        portfolio_grid.addWidget(self.table_portfolio)
        portfolio_gbox.setLayout(portfolio_grid)

        ##### Monitoring items table
        monitoring_items_header = ['Item', 'Time', 'Price', 'Ask', 'Bid']
        monitoring_items_header += ['Volume', 'Volume(A)', 'High', 'Low', 'Open']
        self.table_monitoring_items = QTableWidget(0, 10)
        self.table_monitoring_items.cellClicked.connect(self.on_select_trading_items_table)
        self.table_monitoring_items.setHorizontalHeaderLabels(monitoring_items_header)
        for column in range(1, self.table_monitoring_items.columnCount()):
            self.table_monitoring_items.setColumnWidth(column, 100)
        self.table_monitoring_items.setColumnWidth(0, 215)
        self.table_monitoring_items.setColumnWidth(6, 120)

        monitoring_items_gbox = QGroupBox('Monitoring')
        monitoring_items_grid = QGridLayout()
        monitoring_items_grid.addWidget(self.table_monitoring_items)
        monitoring_items_gbox.setLayout(monitoring_items_grid)

        ##### Balance table
        balance_header = ['Item', 'Current\nPrice', 'Reference\nPrice', 'Purchase\nPrice']
        balance_header += ['Holding\nAmount', 'Purchase\nSum', 'Purchase\nToday', 'Profit\nToday']
        balance_header += ['Profit\nRate', 'Profit\nRealization']
        self.table_balance = QTableWidget(0, 10)
        self.table_balance.cellClicked.connect(self.on_select_balance_table)
        self.table_balance.setHorizontalHeaderLabels(balance_header)
        for column in range(1, self.table_balance.columnCount()):
            self.table_balance.setColumnWidth(column, 100)
        self.table_balance.setColumnWidth(0, 215)
        self.table_balance.setColumnWidth(5, 110)

        balance_gbox = QGroupBox('Balance')
        balance_grid = QGridLayout()
        balance_grid.addWidget(self.table_balance)
        balance_gbox.setLayout(balance_grid)

        ##### Information
        self.te_info = QTextEdit()
        info_grid = QGridLayout()
        info_grid.addWidget(self.te_info, 0, 0)
        info_gbox = QGroupBox('Information')
        info_gbox.setLayout(info_grid)
        info_gbox.setMinimumHeight(500)

        ##### Go Algorithm
        lb_capital = QLabel('Capital')
        self.sb_capital = QSpinBox()
        self.sb_capital.setGroupSeparatorShown(True)
        self.sb_capital.setMinimumHeight(30)
        self.sb_capital.setRange(0, 100000000)
        self.sb_capital.setSingleStep(1000000)
        lb_interval = QLabel('Interval')
        self.sb_interval = QSpinBox()
        self.sb_interval.setMinimumHeight(30)
        self.sb_interval.setRange(0, 300)
        self.sb_interval.setSingleStep(5)
        lb_loss_cut = QLabel('Loss-cut')
        self.sb_loss_cut = QSpinBox()
        self.sb_loss_cut.setMinimumHeight(30)
        self.sb_loss_cut.setRange(0, 200)
        self.sb_loss_cut.setSingleStep(5)
        self.btn_algorithm_set = QPushButton('Set')
        self.btn_algorithm_set.clicked.connect(self.set_algorithm_parameters)
        self.btn_go_algorithm = QPushButton('&Go')
        self.btn_go_algorithm.clicked.connect(self.go)
        self.btn_go_algorithm.setStyleSheet('font-weight:bold; background-color:Goldenrod')
        self.btn_stop_algorithm = QPushButton('&Stop')
        self.btn_stop_algorithm.clicked.connect(self.stop)
        self.btn_stop_algorithm.setStyleSheet('font-weight:bold; background-color:IndianRed')

        # Algorithm inital setting
        self.sb_interval.setValue(50)
        self.sb_loss_cut.setValue(30)
        self.sb_capital.setValue(1000000)

        algorithm_grid = QGridLayout()
        algorithm_grid.addWidget(lb_capital, 0, 0)
        algorithm_grid.addWidget(self.sb_capital, 0, 1)
        algorithm_grid.addWidget(lb_interval, 0, 2)
        algorithm_grid.addWidget(self.sb_interval, 0, 3)
        algorithm_grid.addWidget(lb_loss_cut, 0, 4)
        algorithm_grid.addWidget(self.sb_loss_cut, 0, 5)
        algorithm_grid.addWidget(self.btn_algorithm_set, 0, 6)
        algorithm_grid.addWidget(self.btn_go_algorithm, 0, 7, 1, 15)
        algorithm_grid.addWidget(self.btn_stop_algorithm, 0, 22, 1, 15)
        algorithm_gbox = QGroupBox('Algorithm')
        algorithm_gbox.setLayout(algorithm_grid)

        ##### Open Order Table
        open_orders_header = ['Item', 'Time', 'Order\nAmount', 'Executed\nAmount', 'Open\nAmount']
        open_orders_header += ['Order\nNumber', 'Original\nNumber']
        open_orders_header += ['Order\nPrice', 'Executed\nPrice', 'Order\nPosition', 'Order\nState']
        self.table_open_orders = QTableWidget(0, 11)
        self.table_open_orders.cellClicked.connect(self.on_select_open_orders_table)
        self.table_open_orders.setHorizontalHeaderLabels(open_orders_header)
        for column in range(1, self.table_open_orders.columnCount()):
            self.table_open_orders.setColumnWidth(column, 100)
        self.table_open_orders.setColumnWidth(0, 215)

        open_orders_gbox = QGroupBox('Open Orders')
        open_orders_grid = QGridLayout()
        open_orders_grid.addWidget(self.table_open_orders)
        open_orders_gbox.setLayout(open_orders_grid)
        open_orders_gbox.setMaximumHeight(250)

        ##### Order History Table
        order_history_header = ['Item', 'Time', 'Order\nAmount', 'Executed\nAmount', 'Open\nAmount']
        order_history_header += ['Order\nNumber', 'Original\nNumber', 'Order\nPrice', 'Executed\nPrice']
        order_history_header += ['Order\nPosition', 'Order\nState']
        self.table_order_history = QTableWidget(0, 11)
        self.table_order_history.cellClicked.connect(self.on_select_order_history_table)
        self.table_order_history.setHorizontalHeaderLabels(order_history_header)
        for column in range(1, self.table_order_history.columnCount()):
            self.table_order_history.setColumnWidth(column, 100)
        self.table_order_history.setColumnWidth(0, 215)

        order_history_gbox = QGroupBox('Order History')
        order_history_grid = QGridLayout()
        order_history_grid.addWidget(self.table_order_history)
        order_history_gbox.setLayout(order_history_grid)

        ##### Algorithm Trading Table
        algorithm_trading_header = ['Item', 'Time', 'Order\nNumber', 'Order\nPosition', 'Order\nPrice']
        algorithm_trading_header += ['Executed\nPrice', 'Order\nAmount', 'Executed\nAmount']
        algorithm_trading_header += ['Open\nAmount', 'Profit', 'Total\nProfit']
        self.table_algorithm_trading = QTableWidget(0, 11)
        self.table_algorithm_trading.cellClicked.connect(self.on_select_algorithm_trading_table)
        self.table_algorithm_trading.setHorizontalHeaderLabels(algorithm_trading_header)
        for column in range(1, self.table_algorithm_trading.columnCount()):
            self.table_algorithm_trading.setColumnWidth(column, 100)
        self.table_algorithm_trading.setColumnWidth(0, 215)

        algorithm_trading_gbox = QGroupBox('Algorithm Trading')
        algorithm_trading_grid = QGridLayout()
        algorithm_trading_grid.addWidget(self.table_algorithm_trading)
        algorithm_trading_gbox.setLayout(algorithm_trading_grid)

        ##### Chart Display
        self.fig = plt.Figure()
        self.canvas = FigureCanvas(self.fig)
        canvas_grid = QGridLayout()
        canvas_grid.addWidget(self.canvas, 0, 0)
        canvas_gbox = QGroupBox('Chart')
        canvas_gbox.setLayout(canvas_grid)

        # self.image_view = QGraphicsView()
        # self.image_scene = WookImageScene()
        # self.image_view.adjustSize()
        # self.image_view.setScene(self.image_scene)

        ##### Left Layout #####
        left_top_grid = QGridLayout()
        left_top_grid.addWidget(account_gbox, 0, 0, 1, 3)
        left_top_grid.addWidget(order_gbox, 0, 3, 1, 8)

        left_vbox = QVBoxLayout()
        left_vbox.addLayout(left_top_grid)
        left_vbox.addWidget(portfolio_gbox)
        left_vbox.addWidget(monitoring_items_gbox)
        left_vbox.addWidget(balance_gbox)
        left_vbox.addWidget(info_gbox)
        # left_vbox.addWidget(self.btn_test)

        ##### Right Layout #####
        right_vbox = QVBoxLayout()
        right_vbox.addWidget(algorithm_gbox)
        right_vbox.addWidget(open_orders_gbox)
        right_vbox.addWidget(order_history_gbox)
        right_vbox.addWidget(algorithm_trading_gbox)
        right_vbox.addWidget(canvas_gbox)
        # right_vbox.addWidget(self.image_view)

        ##### Central Layout #####
        central_grid = QGridLayout()
        central_grid.addLayout(left_vbox, 0, 0, 1, 10)
        central_grid.addLayout(right_vbox, 0, 10, 1, 11)

        # Central widget
        cw = QWidget()
        cw.setLayout(central_grid)

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
        self.resize(2550, 1700)
        self.move(100, 100)
        self.setWindowIcon(QIcon('nyang1.ico'))
        self.show()