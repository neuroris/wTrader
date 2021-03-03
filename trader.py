from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog, QTableWidgetSelectionRange
from PyQt5.QtCore import Qt, QThread
import pandas
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from mplfinance.original_flavor import candlestick2_ohlc
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import mplfinance
from datetime import datetime
from traderbase import TraderBase
from kiwoom import Kiwoom
from bankis import Bankis
from wookalgorithm import Algorithm1
from wookitem import Item, Order
from wookutil import WookThreadCollector, ChartDrawer
from wookdata import *
import time, math

class Trader(TraderBase):
    def __init__(self, log, key):
        self.broker = Kiwoom(log, key)
        # self.broker = Bankis(log, key)
        self.algorithm = Algorithm1(log)
        super().__init__(log)

        # Initial work
        self.init_broker()
        self.connect_broker()
        self.get_account_list()
        self.broker.request_deposit_info()
        self.broker.request_portfolio_info()
        self.broker.request_order_history()
        self.init_algorithm()

        # Init Fields
        self.interval = self.sb_interval.value()
        self.loss_cut = self.sb_loss_cut.value()

        ### For debugging convenience
        # self.cbb_item_code.setCurrentIndex(2)
        # self.sb_price.setValue(30000)
        self.sb_amount.setValue(10)
        # self.cbb_order_position.setCurrentIndex(1)

    def test1(self):
        self.debug('test1 button clicked')

        item = Item()
        item.current_price = int(self.le_test.text())
        self.algorithm.update_transaction_info(item)

    def test2(self):
        self.debug('test2 button clicked')

        order = Order()
        order.item_code = '122630'
        order.order_price = 30000
        order.order_position = SELL
        order.order_amount = 10
        order.open_amount = 10
        order.order_number = int(self.le_order_number.text())
        order.current_price = int(self.le_test.text())
        self.algorithm.update_execution_info(order)

    def connect_broker(self):
        # if self.cb_auto_login.isChecked():
        #     self.broker.auto_login()
        # else:
        #     self.broker.login()
        #     self.broker.set_account_password()

        self.broker.auto_login()


    def init_broker(self):
        self.broker.log = self.log
        self.broker.signal = self.on_kiwoom_signal
        self.broker.status = self.status
        self.broker.draw_chart.set(self.display_chart)
        self.broker.algorithm = self.algorithm

    def init_algorithm(self):
        self.algorithm.signal = self.on_algorithm_signal

    def get_account_list(self):
        account_list = self.broker.get_account_list()
        if account_list is not None:
            self.cbb_account.addItems(self.broker.account_list)

    def get_deposit(self):
        self.broker.request_deposit_info()

    def get_portfolio(self):
        self.broker.request_portfolio_info()

    def get_order_history(self):
        item_code = self.cbb_item_code.currentText()
        self.broker.order_history.clear()
        self.broker.request_order_history(item_code)

    def go_chart(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        self.broker.go_chart(item_code)
        self.info('Go Charting', item_name)

    def stop_chart(self):
        self.broker.stop_chart()

    def send_order(self):
        item_code = self.cbb_item_code.currentText()
        order_position = self.cbb_order_position.currentText()
        price = self.sb_price.value()
        amount = self.sb_amount.value()
        order_type = self.cbb_order_type.currentText()
        order_number = self.le_order_number.text()

        self.broker.order(item_code, price, amount, order_position, order_type, order_number)

    def update_deposit_info(self):
        deposit = '\\' + self.formalize(self.broker.deposit)
        orderable_money = '\\' + self.formalize(self.broker.orderable_money)
        self.lb_deposit.setText(deposit)
        self.lb_orderable.setText(orderable_money)

    def update_order_variables(self):
        if not self.broker.account_number:
            return

        item = Item()
        item_code = self.cbb_item_code.currentText()
        if item_code in self.broker.portfolio:
            item = self.broker.portfolio[item_code]

        buyable_amount = 'no info'
        if item.current_price != 0:
            buyable_amount = self.formalize(self.broker.orderable_money // item.current_price)
        self.lb_buyable.setText(buyable_amount)
        self.lb_sellable.setText(self.formalize(item.holding_amount))
        self.sb_price.setValue(item.current_price)

    def go(self):
        interval = self.sb_interval.value()
        loss_cut = self.sb_loss_cut.value()
        capital = self.sb_capital.value()
        self.algorithm.start(self.broker, capital, interval, loss_cut)
        self.log('Algorithm started')

    def stop(self):
        self.algorithm.stop()
        self.log('Algorithm stopped')

    def display_portfolio(self):
        self.clear_table(self.table_portfolio)
        for row, item in enumerate(self.broker.portfolio.values()):
            self.table_portfolio.insertRow(row)
            self.table_portfolio.setRowHeight(row, 8)
            self.table_portfolio.setItem(row, 0, self.to_item(item.item_name))
            self.table_portfolio.setItem(row, 1, self.to_item(item.current_price))
            self.table_portfolio.setItem(row, 2, self.to_item(item.purchase_price))
            self.table_portfolio.setItem(row, 3, self.to_item(item.holding_amount))
            self.table_portfolio.setItem(row, 4, self.to_item(item.purchase_sum))
            self.table_portfolio.setItem(row, 5, self.to_item(item.evaluation_sum))
            self.table_portfolio.setItem(row, 6, self.to_item(item.total_fee))
            self.table_portfolio.setItem(row, 7, self.to_item(item.tax))
            self.table_portfolio.setItem(row, 8, self.to_item_sign(item.profit))
            self.table_portfolio.setItem(row, 9, self.to_item_sign(item.profit_rate))
        self.table_portfolio.sortItems(0, Qt.DescendingOrder)

    def display_monitoring_items(self):
        self.clear_table(self.table_monitoring_items)
        for row, item in enumerate(self.broker.monitoring_items.values()):
            self.table_monitoring_items.insertRow(row)
            self.table_monitoring_items.setRowHeight(row, 8)
            self.table_monitoring_items.setItem(row, 0, self.to_item(item.item_name))
            self.table_monitoring_items.setItem(row, 1, self.to_item_time(item.transaction_time))
            self.table_monitoring_items.setItem(row, 2, self.to_item(item.current_price))
            self.table_monitoring_items.setItem(row, 3, self.to_item(item.ask_price))
            self.table_monitoring_items.setItem(row, 4, self.to_item(item.bid_price))
            self.table_monitoring_items.setItem(row, 5, self.to_item(item.volume))
            self.table_monitoring_items.setItem(row, 6, self.to_item(item.accumulated_volume))
            self.table_monitoring_items.setItem(row, 7, self.to_item(item.high_price))
            self.table_monitoring_items.setItem(row, 8, self.to_item(item.low_price))
            self.table_monitoring_items.setItem(row, 9, self.to_item(item.open_price))
        self.table_monitoring_items.sortItems(0, Qt.DescendingOrder)

    def display_balance(self):
        self.clear_table(self.table_balance)
        for row, item in enumerate(self.broker.balance.values()):
            self.table_balance.insertRow(row)
            self.table_balance.setRowHeight(row, 8)
            self.table_balance.setItem(row, 0, self.to_item(item.item_name))
            self.table_balance.setItem(row, 1, self.to_item(item.current_price))
            self.table_balance.setItem(row, 2, self.to_item(item.reference_price))
            self.table_balance.setItem(row, 3, self.to_item(item.purchase_price_avg))
            self.table_balance.setItem(row, 4, self.to_item(item.holding_amount))
            self.table_balance.setItem(row, 5, self.to_item(item.purchase_sum))
            self.table_balance.setItem(row, 6, self.to_item_sign(item.purchase_amount_net_today))
            self.table_balance.setItem(row, 7, self.to_item_sign(item.balance_profit_net_today))
            self.table_balance.setItem(row, 8, self.to_item_sign(item.balance_profit_rate))
            self.table_balance.setItem(row, 9, self.to_item_sign(item.balance_profit_realization))
        self.table_balance.sortItems(0, Qt.DescendingOrder)

    def display_open_orders(self):
        self.clear_table(self.table_open_orders)
        for row, order in enumerate(self.broker.open_orders.values()):
            self.table_open_orders.insertRow(row)
            self.table_open_orders.setRowHeight(row, 8)
            self.table_open_orders.setItem(row, 0, self.to_item(order.item_name))
            self.table_open_orders.setItem(row, 1, self.to_item_time(order.order_executed_time))
            self.table_open_orders.setItem(row, 2, self.to_item(order.order_amount))
            self.table_open_orders.setItem(row, 3, self.to_item(order.executed_amount_sum))
            self.table_open_orders.setItem(row, 4, self.to_item(order.open_amount))
            self.table_open_orders.setItem(row, 5, self.to_item_plain(order.order_number))
            self.table_open_orders.setItem(row, 6, self.to_item_plain(order.original_order_number))
            self.table_open_orders.setItem(row, 7, self.to_item(order.order_price))
            self.table_open_orders.setItem(row, 8, self.to_item(order.executed_price_avg))
            self.table_open_orders.setItem(row, 9, self.to_item_center(order.order_position))
            self.table_open_orders.setItem(row, 10, self.to_item_center(order.order_state))
        self.table_open_orders.sortItems(1, Qt.DescendingOrder)

    def display_order_history(self):
        self.clear_table(self.table_order_history)
        for row, order in enumerate(self.broker.order_history.values()):
            self.table_order_history.insertRow(row)
            self.table_order_history.setRowHeight(row, 8)
            self.table_order_history.setItem(row, 0, self.to_item(order.item_name))
            self.table_order_history.setItem(row, 1, self.to_item_time(order.order_executed_time))
            self.table_order_history.setItem(row, 2, self.to_item(order.order_amount))
            self.table_order_history.setItem(row, 3, self.to_item(order.executed_amount_sum))
            self.table_order_history.setItem(row, 4, self.to_item(order.open_amount))
            self.table_order_history.setItem(row, 5, self.to_item_plain(order.order_number))
            self.table_order_history.setItem(row, 6, self.to_item_plain(order.original_order_number))
            self.table_order_history.setItem(row, 7, self.to_item(order.order_price))
            self.table_order_history.setItem(row, 8, self.to_item(order.executed_price_avg))
            self.table_order_history.setItem(row, 9, self.to_item_center(order.order_position))
            self.table_order_history.setItem(row, 10, self.to_item_center(order.order_state))
        self.table_order_history.sortItems(1, Qt.DescendingOrder)

    def display_algorithm_trading(self):
        self.clear_table(self.table_algorithm_trading)
        for row, order in enumerate(self.algorithm.orders.values()):
            self.table_algorithm_trading.insertRow(row)
            self.table_algorithm_trading.setRowHeight(row, 8)
            self.table_algorithm_trading.setItem(row, 0, self.to_item(order.item_name))
            self.table_algorithm_trading.setItem(row, 1, self.to_item_time(order.order_executed_time))
            self.table_algorithm_trading.setItem(row, 2, self.to_item_plain(order.order_number))
            self.table_algorithm_trading.setItem(row, 3, self.to_item_center(order.order_position))
            self.table_algorithm_trading.setItem(row, 4, self.to_item_center(order.order_state))
            self.table_algorithm_trading.setItem(row, 5, self.to_item(order.order_price))
            self.table_algorithm_trading.setItem(row, 6, self.to_item(order.executed_price_avg))
            self.table_algorithm_trading.setItem(row, 7, self.to_item(order.order_amount))
            self.table_algorithm_trading.setItem(row, 8, self.to_item(order.executed_amount_sum))
            self.table_algorithm_trading.setItem(row, 9, self.to_item_sign(order.open_amount))
            self.table_algorithm_trading.setItem(row, 10, self.to_item_sign(order.profit))
        self.table_algorithm_trading.sortItems(2, Qt.DescendingOrder)

    def clear_table(self, table):
        for row in range(table.rowCount()):
            table.removeRow(0)

    def display_algorithm_profit(self):
        total_profit = self.algorithm.leverage.profit
        formalized_profit = self.formalize(total_profit)
        profit_rate = round(total_profit / self.sb_capital.value() * 100, 2)
        profit_display = '{} ({}%)'.format(formalized_profit, profit_rate)
        self.lb_total_profit.setText(profit_display)

    def display_chart(self):
        if not self.broker.chart_prices:
            return

        self.fig.clear()
        ax = self.fig.add_subplot(1, 1, 1)

        df = pandas.DataFrame(self.broker.chart_prices, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df.Time = pandas.to_datetime(df.Time)

        # Axis ticker formatting
        locator = list()
        formatter = list()
        for index in range(0, len(df.Time), 30):
            time_format = df.Time.iloc[index].strftime('%H:%M')
            locator.append(index)
            formatter.append(time_format)
        ax.xaxis.set_major_locator(ticker.FixedLocator(locator))
        ax.xaxis.set_major_formatter(ticker.FixedFormatter(formatter))
        # ax.set_xticklabels(time_int, rotation=75)

        max_price = df.High.max()
        min_price = df.Low.min()
        max_ceiling = math.ceil(max_price / self.interval) * self.interval
        min_floor = math.floor(min_price / self.interval) * self.interval
        ortho_prices = list(range(min_floor, max_ceiling + self.interval, self.interval))
        loss_cut_prices = list(range(min_floor + self.interval - self.loss_cut, max_ceiling, self.interval))
        ax.grid(axis='x', alpha=0.5)
        # ax.grid(axis='both', alpha=0.5)
        ## arrow = dict(arrowstyle='->')
        ## ax.annotate('buy', xy=(30, 28300), xytext=(50, 28200), color='green', arrowprops=arrow)
        ax.set_yticks(ortho_prices)
        for price in ortho_prices:
            ax.axhline(price, alpha=0.5, linewidth=0.2)
        for price in loss_cut_prices:
            ax.axhline(price, alpha=0.4, linewidth=0.2, color='Gray')

        # Current Price Annotation
        current_time = self.to_min_count(self.broker.chart_prices[-1][TIME_][8:12])
        current_price = self.broker.chart_prices[-1][CLOSE]
        ax.text(current_time + 2, current_price, format(current_price, ','))

        # Algorithm Annotations
        if self.algorithm.is_running and self.algorithm.start_price:
            self.annotate_chart(ax, min_floor)

        # Draw Chart
        candlestick2_ohlc(ax, df['Open'], df['High'], df['Low'], df['Close'], width=0.4, colorup='r', colordown='b')
        self.fig.tight_layout()
        self.canvas.draw()

    def annotate_chart(self, ax, min_floor):
        start_time = self.algorithm.start_time
        start_price = self.algorithm.start_price
        start_comment = 'start\n' + self.algorithm.start_time_text + '\n' + format(start_price, ',')
        ax.plot(start_time, start_price, marker='o', markersize=3, color='Lime')
        ax.vlines(start_time, min_floor, start_price, alpha=0.8, linewidth=0.2, color='Green')
        ax.text(start_time, min_floor, start_comment, color='RebeccaPurple')
        ax.axhline(self.algorithm.reference_price, alpha=1, linewidth=0.2, color='Maroon')
        ax.text(0, self.algorithm.reference_price, 'Reference')
        ax.axhline(self.algorithm.buy_limit, alpha=1, linewidth=0.2, color='LimeGreen')
        ax.text(0, self.algorithm.buy_limit, 'Buy limit')

        ax.axhline(self.algorithm.loss_limit, alpha=1, linewidth=0.2, color='Red')
        ax.text(0, self.algorithm.loss_limit, 'Loss cut')

        # if self.algorithm.orders:
        #     ax.axhline(self.algorithm.loss_limit, alpha=1, linewidth=0.2, color='Red')
        #     ax.text(0, self.algorithm.loss_limit, 'Loss cut')

    # def on_select_broker(self, broker):
    #     if broker == 'Kiwoom':
    #         self.broker = self.kiwoom
    #         self.info('Kiwoom is selected for broker')
    #     elif broker == 'Bankis':
    #         self.broker = self.bankis
    #         self.info('Bankis is selected for broker')

    def on_select_account(self, account):
        self.broker.account_number = int(account)

    def on_select_item_code(self, item_code):
        item_name = CODES.get(item_code)
        if item_name is None:
            item_name = self.broker.get_item_name(item_code)
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
        item_code = self.broker.get_item_code(item_name)
        self.cbb_item_code.setCurrentText(item_code)

    def on_add_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code in self.broker.monitoring_items:
            return

        item = Item()
        item.item_code = item_code
        item.item_name = item_name
        self.broker.demand_monitoring_items_info(item)
        self.display_monitoring_items()
        self.info(item.item_name, 'trading information begins to be monitored')

    def on_remove_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code not in self.broker.monitoring_items:
            return

        # self.table_trading_items.removeRow(0)

        self.broker.init_screen(item_code)
        del self.broker.monitoring_items[item_code]
        self.table_monitoring_items.clearContents()
        self.display_monitoring_items()
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

        holding_amount_column = 3
        holding_amount_item = self.table_portfolio.item(row, holding_amount_column)
        holding_amount = self.process_type(holding_amount_item.text())
        self.sb_amount.setValue(holding_amount)

    def on_select_trading_items_table(self, row, column):
        column_count = self.table_monitoring_items.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_monitoring_items.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_monitoring_items.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 2
        current_price_item = self.table_monitoring_items.item(row, current_price_column)
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

        order_number_column = 2
        order_number_item = self.table_algorithm_trading.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 5
        order_price_item = self.table_algorithm_trading.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

        open_amount_column = 9
        open_amount_item = self.table_algorithm_trading.item(row, open_amount_column)
        open_amount = int(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

    def set_algorithm_parameters(self):
        self.interval = self.sb_interval.value()
        self.loss_cut = self.sb_loss_cut.value()
        self.algorithm.capital = self.sb_capital.value()
        self.algorithm.interval = self.interval
        self.algorithm.loss_cut = self.loss_cut

    def on_edit_save_file(self):
        file = self.le_save_file.text()
        self.broker.log_file = file

    def on_change_save_file(self):
        file = QFileDialog.getOpenFileName(self, 'Select File', self.setting['save_folder'])[0]
        if file != '':
            self.le_save_file.setText(file)
            self.broker.log_file = file

    def edit_setting(self):
        self.debug('setting')

    def on_kiwoom_signal(self, signal, *args):
        if signal == 'deposit':
            self.update_deposit_info()
        elif signal == 'portfolio':
            self.update_order_variables()
        elif signal == 'portfolio_table':
            self.display_portfolio()
        elif signal == 'monitoring_items_table':
            self.display_monitoring_items()
        elif signal == 'balance_table':
            self.display_balance()
        elif signal == 'open_orders_table':
            self.display_open_orders()
        elif signal == 'order_history_table':
            self.display_order_history()
        elif signal == 'algorithm_trading_table':
            self.display_algorithm_trading()
        elif signal == 'chart':
            self.display_chart()

    def on_algorithm_signal(self, signal, *args):
        if signal == 'total_profit':
            # self.lb_total_profit.setText(self.formalize(self.algorithm.leverage.total_profit))
            self.display_algorithm_profit()
        elif signal == 'algorithm_trading_table':
            self.display_algorithm_trading()

    def log(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        current_time = datetime.now().strftime('%H:%M:%S') + ' '
        self.te_info.append(current_time + message)
        self.info(message)

    def status(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        self.status_bar.showMessage(message)

    def closeEvent(self, event):
        self.broker.log('Closing process initializing...')
        self.broker.close_process()
        self.broker.clear()
        self.broker.deleteLater()
        self.deleteLater()