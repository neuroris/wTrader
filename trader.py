from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog, QTableWidgetSelectionRange
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QPixmap
import pandas
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from mplfinance.original_flavor import candlestick2_ohlc
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import mplfinance
from datetime import datetime
from traderbase import TraderBase
from kiwoom import Kiwoom
from wookstock import Stock
from wookutil import WookThreadCollector, ChartDrawer
from wookdata import *
import time, math

class Trader(TraderBase):
    def __init__(self, log, key):
        self.kiwoom = Kiwoom(log, key)
        # self.thread_collector = WookThreadCollector(self.kiwoom, log)
        super().__init__(log)

        # Initial work
        self.initKiwoom()
        self.connect_kiwoom()
        self.kiwoom.request_deposit_info()
        self.kiwoom.request_portfolio_info()
        self.kiwoom.request_order_history()
        # self.thread_collector.start()

        # For debugging convenience
        # self.cbb_item_code.setCurrentIndex(2)

    def test(self):
        self.debug('test button clicked')
        item_code = self.cbb_item_code.currentText()

        self.kiwoom.deposit_requester.start()

        # import random
        # price = random.randrange(20000, 25000, 5)
        # self.kiwoom.update_chart_prices(price, 200)

    def initKiwoom(self):
        self.kiwoom.log = self.on_kiwoom_log
        self.kiwoom.signal = self.on_kiwoom_signal
        self.kiwoom.status = self.on_kiwoom_status
        self.kiwoom.draw_chart.set(self.display_chart)

    def connect_kiwoom(self):
        if self.cb_auto_login.isChecked():
            self.kiwoom.auto_login()
        else:
            self.kiwoom.login()
            self.kiwoom.set_account_password()

        self.get_account_list()

    def get_account_list(self):
        account_list = self.kiwoom.get_account_list()
        if account_list is not None:
            self.cbb_account.addItems(self.kiwoom.account_list)

    def get_deposit(self):
        self.kiwoom.request_deposit_info()

    def get_portfolio(self):
        self.kiwoom.request_portfolio_info()

    def get_order_history(self):
        item_code = self.cbb_item_code.currentText()
        self.kiwoom.request_order_history(item_code)

    def go_chart(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        self.kiwoom.go_chart(item_code)
        self.info('Go Charting', item_name)

    def stop_chart(self):
        self.kiwoom.stop_chart()
        self.info('Stop Charting')

    def send_order(self):
        item_code = self.cbb_item_code.currentText()
        order_position = self.cbb_order_position.currentText()
        price = self.sb_price.value()
        amount = self.sb_amount.value()
        order_type = ORDER_TYPE[self.cbb_order_type.currentText()]
        order_number = self.le_order_number.text()
        if order_type == ORDER_TYPE['MARKET']:
            price = 0

        self.kiwoom.order(item_code, price, amount, order_position, order_type, order_number)

    def update_deposit_info(self):
        deposit = '\\' + self.formalize(self.kiwoom.deposit)
        orderable_money = '\\' + self.formalize(self.kiwoom.orderable_money)
        self.lb_deposit.setText(deposit)
        self.lb_orderable.setText(orderable_money)

    def update_order_variables(self):
        if not self.kiwoom.account_number:
            return

        stock = Stock()
        item_code = self.cbb_item_code.currentText()
        if item_code in self.kiwoom.portfolio:
            stock = self.kiwoom.portfolio[item_code]

        buyable_amount = 'no info'
        if stock.current_price != 0:
            buyable_amount = self.formalize(self.kiwoom.orderable_money // stock.current_price)
        self.lb_buyable.setText(buyable_amount)
        self.lb_sellable.setText(self.formalize(stock.holding_amount))
        self.sb_price.setValue(stock.current_price)

    def go(self):
        self.kiwoom.execute_algorithm()

    def display_portfolio(self):
        self.clear_table(self.table_portfolio)
        for row, stock in enumerate(self.kiwoom.portfolio.values()):
            self.table_portfolio.insertRow(row)
            self.table_portfolio.setRowHeight(row, 8)
            self.table_portfolio.setItem(row, 0, self.to_item(stock.item_name))
            self.table_portfolio.setItem(row, 1, self.to_item(stock.current_price))
            self.table_portfolio.setItem(row, 2, self.to_item(stock.purchase_price))
            self.table_portfolio.setItem(row, 3, self.to_item(stock.holding_amount))
            self.table_portfolio.setItem(row, 4, self.to_item(stock.purchase_sum))
            self.table_portfolio.setItem(row, 5, self.to_item(stock.evaluation_sum))
            self.table_portfolio.setItem(row, 6, self.to_item(stock.total_fee))
            self.table_portfolio.setItem(row, 7, self.to_item(stock.tax))
            self.table_portfolio.setItem(row, 8, self.to_item_sign(stock.profit))
            self.table_portfolio.setItem(row, 9, self.to_item_sign(stock.profit_rate))
        self.table_portfolio.sortItems(0, Qt.DescendingOrder)

    def display_trading_items(self):
        for row, stock in enumerate(self.kiwoom.trading_items.values()):
            self.table_trading_items.setItem(row, 0, self.to_item(stock.item_name))
            self.table_trading_items.setItem(row, 1, self.to_item_time(stock.transaction_time))
            self.table_trading_items.setItem(row, 2, self.to_item(stock.current_price))
            self.table_trading_items.setItem(row, 3, self.to_item(stock.ask_price))
            self.table_trading_items.setItem(row, 4, self.to_item(stock.bid_price))
            self.table_trading_items.setItem(row, 5, self.to_item(stock.volume))
            self.table_trading_items.setItem(row, 6, self.to_item(stock.accumulated_volume))
            self.table_trading_items.setItem(row, 7, self.to_item(stock.high_price))
            self.table_trading_items.setItem(row, 8, self.to_item(stock.low_price))
            self.table_trading_items.setItem(row, 9, self.to_item(stock.open_price))
        self.table_trading_items.sortItems(0, Qt.DescendingOrder)

    def display_balance(self):
        self.clear_table(self.table_balance)
        for row, stock in enumerate(self.kiwoom.balance.values()):
            self.table_balance.insertRow(row)
            self.table_balance.setRowHeight(row, 8)
            self.table_balance.setItem(row, 0, self.to_item(stock.item_name))
            self.table_balance.setItem(row, 1, self.to_item(stock.current_price))
            self.table_balance.setItem(row, 2, self.to_item(stock.reference_price))
            self.table_balance.setItem(row, 3, self.to_item(stock.purchase_price_avg))
            self.table_balance.setItem(row, 4, self.to_item(stock.holding_amount))
            self.table_balance.setItem(row, 5, self.to_item(stock.purchase_sum))
            self.table_balance.setItem(row, 6, self.to_item_sign(stock.purchase_amount_net_today))
            self.table_balance.setItem(row, 7, self.to_item_sign(stock.balance_profit_net_today))
            self.table_balance.setItem(row, 8, self.to_item_sign(stock.balance_profit_rate))
            self.table_balance.setItem(row, 9, self.to_item_sign(stock.balance_profit_realization))
        self.table_balance.sortItems(0, Qt.DescendingOrder)

    def display_open_orders(self):
        self.clear_table(self.table_open_orders)
        for row, stock in enumerate(self.kiwoom.open_orders.values()):
            self.table_open_orders.insertRow(row)
            self.table_open_orders.setRowHeight(row, 8)
            self.table_open_orders.setItem(row, 0, self.to_item(stock.item_name))
            self.table_open_orders.setItem(row, 1, self.to_item_time(stock.order_executed_time))
            self.table_open_orders.setItem(row, 2, self.to_item(stock.order_amount))
            self.table_open_orders.setItem(row, 3, self.to_item(stock.executed_amount_sum))
            self.table_open_orders.setItem(row, 4, self.to_item(stock.open_amount))
            self.table_open_orders.setItem(row, 5, self.to_item_plain(stock.order_number))
            self.table_open_orders.setItem(row, 6, self.to_item_plain(stock.original_order_number))
            self.table_open_orders.setItem(row, 7, self.to_item(stock.order_price))
            self.table_open_orders.setItem(row, 8, self.to_item(stock.executed_price_average))
            self.table_open_orders.setItem(row, 9, self.to_item_center(stock.order_position))
            self.table_open_orders.setItem(row, 10, self.to_item_center(stock.order_state))
        self.table_open_orders.sortItems(1, Qt.DescendingOrder)

    def display_order_history(self):
        self.clear_table(self.table_order_history)
        for row, stock in enumerate(self.kiwoom.order_history.values()):
            self.table_order_history.insertRow(row)
            self.table_order_history.setRowHeight(row, 8)
            self.table_order_history.setItem(row, 0, self.to_item(stock.item_name))
            self.table_order_history.setItem(row, 1, self.to_item_time(stock.order_executed_time))
            self.table_order_history.setItem(row, 2, self.to_item(stock.order_amount))
            self.table_order_history.setItem(row, 3, self.to_item(stock.executed_amount_sum))
            self.table_order_history.setItem(row, 4, self.to_item(stock.open_amount))
            self.table_order_history.setItem(row, 5, self.to_item_plain(stock.order_number))
            self.table_order_history.setItem(row, 6, self.to_item_plain(stock.original_order_number))
            self.table_order_history.setItem(row, 7, self.to_item(stock.order_price))
            self.table_order_history.setItem(row, 8, self.to_item(stock.executed_price_average))
            self.table_order_history.setItem(row, 9, self.to_item_center(stock.order_position))
            self.table_order_history.setItem(row, 10, self.to_item_center(stock.order_state))
        self.table_order_history.sortItems(1, Qt.DescendingOrder)

    def display_algorithm_trading(self):
        self.clear_table(self.table_algorithm_trading)
        for row, stock in enumerate(self.kiwoom.algorithm_manager.get_stocks().values()):
            self.table_algorithm_trading.insertRow(row)
            self.table_algorithm_trading.setRowHeight(row, 8)
            self.table_algorithm_trading.setItem(row, 0, self.to_item(stock.item_name))
            self.table_algorithm_trading.setItem(row, 1, self.to_item_center(stock.trade_position))
            self.table_algorithm_trading.setItem(row, 2, self.to_item(stock.current_price))
            self.table_algorithm_trading.setItem(row, 3, self.to_item(stock.order_price))
            self.table_algorithm_trading.setItem(row, 4, self.to_item(stock.executed_price_average))
            self.table_algorithm_trading.setItem(row, 5, self.to_item_plain(stock.order_number))
            self.table_algorithm_trading.setItem(row, 6, self.to_item(stock.order_amount))
            self.table_algorithm_trading.setItem(row, 7, self.to_item(stock.executed_amount_sum))
            self.table_algorithm_trading.setItem(row, 8, self.to_item_sign(stock.open_amount))
            self.table_algorithm_trading.setItem(row, 9, self.to_item_sign(stock.profit))
            self.table_algorithm_trading.setItem(row, 10, self.to_item_sign(stock.profit_rate))
        self.table_algorithm_trading.sortItems(0, Qt.DescendingOrder)

    def clear_table(self, table):
        for row in range(table.rowCount()):
            table.removeRow(0)

    def display_chart(self):
        if not self.kiwoom.chart_prices:
            return
        current_time = datetime.now().strftime('%Y%m%d%H%M')


        # max = df['Price'].max()
        # min = df['Price'].min()
        # max_ceiling = math.ceil(max / interval) * interval
        # min_floor = math.floor(min / interval) * interval
        # yticks = list(range(min_floor, max_ceiling + interval, interval))

        df = pandas.DataFrame(self.kiwoom.chart_prices, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])

        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)

        # a = df['Time'].astype(int)
        # dd = a.tolist()
        time_column = df.Time
        time_list = time_column.tolist()
        time_int = list(map(int, time_list))
        ax.tick_params(axis='x', labelsize=10)
        ax.set_xticks(time_int)
        ax.set_xticklabels(time_int, rotation=75)

        # ax.clear()
        candlestick2_ohlc(ax, df['Open'], df['High'], df['Low'], df['Close'], width=0.4, colorup='r', colordown='b')
        self.fig.tight_layout()
        self.canvas.draw()

    def on_select_account(self, account):
        self.kiwoom.account_number = int(account)

    def on_select_item_code(self, item_code):
        item_name = CODES.get(item_code)
        if item_name is None:
            item_name = self.kiwoom.get_item_name(item_code)
            if item_name != '':
                CODES[item_code] = item_name
                self.cbb_item_code.addItem(item_code)
                self.cbb_item_name.addItem(item_name)

        if item_code[:3] == FUTURES_CODE:
            self.cbb_order_type.clear()
            self.cbb_order_type.addItems(FUTURES_ORDER_TYPE)
        else:
            self.cbb_order_type.clear()
            self.cbb_order_type.addItems(ORDER_TYPE)

        self.cbb_item_name.setCurrentText(item_name)
        self.update_order_variables()

    def on_select_item_name(self, index):
        item_name = self.cbb_item_name.currentText()
        item_code = self.kiwoom.get_item_code(item_name)
        self.cbb_item_code.setCurrentText(item_code)

    def on_add_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code in self.kiwoom.trading_items:
            return

        row = len(self.kiwoom.trading_items)
        self.table_trading_items.insertRow(row)
        self.table_trading_items.setRowHeight(row, 8)

        stock = Stock()
        stock.item_code = item_code
        stock.item_name = item_name
        self.kiwoom.trading_items[item_code] = stock
        self.display_trading_items()
        self.kiwoom.demand_trading_item_info(item_code)
        self.info(stock.item_name, 'trading information begins to be monitored')

    def on_remove_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code not in self.kiwoom.trading_items:
            return

        self.table_trading_items.removeRow(0)

        self.kiwoom.init_screen(item_code)
        del self.kiwoom.trading_items[item_code]
        self.table_trading_items.clearContents()
        self.display_trading_items()
        self.info(item_name, 'stock information monitoring is finished')

    def on_select_portfolio_table(self, row, column):
        column_count = self.table_portfolio.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_portfolio.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_portfolio.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 1
        current_price_item = self.table_portfolio.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

    def on_select_trading_items_table(self, row, column):
        column_count = self.table_trading_items.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_trading_items.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_trading_items.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 2
        current_price_item = self.table_trading_items.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

    def on_select_balance_table(self, row, column):
        column_count = self.table_balance.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_balance.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_balance.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 1
        current_price_item = self.table_balance.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

    def on_select_open_orders_table(self, row, column):
        column_count = self.table_order_history.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_open_orders.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_open_orders.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        open_amount_column = 4
        open_amount_item = self.table_open_orders.item(row, open_amount_column)
        open_amount = int(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

        order_number_column = 5
        order_number_item = self.table_open_orders.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 7
        order_price_item = self.table_open_orders.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

    def on_select_order_history_table(self, row, column):
        column_count = self.table_order_history.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_order_history.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_order_history.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        open_amount_column = 4
        open_amount_item = self.table_order_history.item(row, open_amount_column)
        open_amount = self.process_type(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

        order_number_column = 5
        order_number_item = self.table_order_history.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 7
        order_price_item = self.table_order_history.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

    def on_select_algorithm_trading_table(self, row, column):
        column_count = self.table_algorithm_trading.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_algorithm_trading.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_algorithm_trading.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        order_price_column = 3
        order_price_item = self.table_algorithm_trading.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

        order_number_column = 5
        order_number_item = self.table_algorithm_trading.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        open_amount_column = 8
        open_amount_item = self.table_open_orders.item(row, open_amount_column)
        open_amount = int(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

    def on_edit_save_file(self):
        file = self.le_save_file.text()
        self.kiwoom.log_file = file

    def on_change_save_file(self):
        file = QFileDialog.getOpenFileName(self, 'Select File', self.setting['save_folder'])[0]
        if file != '':
            self.le_save_file.setText(file)
            self.kiwoom.log_file = file

    def edit_setting(self):
        self.debug('setting')

    def on_kiwoom_signal(self, signal, *args):
        if signal == 'deposit':
            self.update_deposit_info()
        elif signal == 'portfolio':
            self.update_order_variables()
        elif signal == 'portfolio_table':
            self.display_portfolio()
        elif signal == 'trading_items_table':
            self.display_trading_items()
        elif signal == 'balance_table':
            self.display_balance()
        elif signal == 'open_orders_table':
            self.display_open_orders()
        elif signal == 'algorithm_trading_table':
            self.display_algorithm_trading()
        elif signal == 'order_history_table':
            self.display_order_history()
        elif signal == 'chart':
            self.display_chart()

    def on_kiwoom_log(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        time = datetime.now().strftime('%H:%M:%S') + ' '
        self.te_info.append(time + message)
        self.info(message)

    def on_kiwoom_status(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        self.status_bar.showMessage(message)

    def closeEvent(self, event):
        self.kiwoom.log('Closing process initializing...')
        self.kiwoom.close_process()
        self.kiwoom.clear()
        self.kiwoom.deleteLater()
        self.deleteLater()