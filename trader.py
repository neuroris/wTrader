from PyQt5.QtWidgets import QFileDialog, QTableWidgetSelectionRange
from PyQt5.QtCore import Qt, QTimer, QThread
import numpy as np
import pandas
from matplotlib import ticker, pyplot
from mplfinance.original_flavor import candlestick2_ohlc
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from datetime import datetime
from traderbase import TraderBase
from kiwoom import Kiwoom
from wookutil import wmath
from wookitem import FuturesAlgorithmItem
from wookalgorithm.quantumjump.algorithm1 import QAlgorithm1
from wookalgorithm.quantumjump.algorithm2 import QAlgorithm2
from wookalgorithm.quantumjump.algorithm4 import QAlgorithm4
from wookalgorithm.quantumjump.algorithm5 import QAlgorithm5
from wookalgorithm.volatility.algorithm3 import VAlgorithm3
from wookalgorithm.volatility.algorithm4 import VAlgorithm4
from wookalgorithm.volatility.algorithm5 import VAlgorithm5
from wookalgorithm.volatility.algorithm6 import VAlgorithm6
from wookalgorithm.movingaverage.algorithm1 import MAlgorithm1
from wookalgorithm.movingaverage.algorithm2 import MAlgorithm2
from wookalgorithm.movingaverage.algorithm3 import MAlgorithm3
from wookalgorithm.futures.algorithm1 import FMAlgorithm1
from wookalgorithm.futures.algorithm2 import FMAlgorithm2
from wookalgorithm.futures.algorithm3 import FMAlgorithm3
from wookalgorithm.futures.algorithm4 import FMAlgorithm4
from wookalgorithm.futures.algorithm5 import FMAlgorithm5
from wookalgorithm.futures.algorithm6 import FMAlgorithm6
from wookalgorithm.futures.algorithm7 import FMAlgorithm7
from wookalgorithm.futures.algorithm8 import FMAlgorithm8
from wookalgorithm.futures.algorithm9 import FMAlgorithm9
from wookalgorithm.futures.algorithm10 import FMAlgorithm10
from wookalgorithm.futures.algorithm11 import FMAlgorithm11
from wookalgorithm.futures.algorithm12 import FMAlgorithm12
from wookalgorithm.futures.algorithm20 import FMAlgorithm20
from wookalgorithm.futures.algorithm30 import FMAlgorithm30
from wookalgorithm.futures.algorithm31 import FMAlgorithm31
from wookalgorithm.futures.algorithm32 import FMAlgorithm32
from wookalgorithm.futures.algorithm33 import FMAlgorithm33
from wookalgorithm.futures.algorithm39 import FMAlgorithm39
from wookalgorithm.futures.algorithm40 import FMAlgorithm40
from wookalgorithm.futures.algorithm41 import FMAlgorithm41
from wookalgorithm.futures.algorithm42 import FMAlgorithm42
from wookalgorithm.futures.algorithm43 import FMAlgorithm43
from wookalgorithm.futures.algorithm44 import FMAlgorithm44
from wookalgorithm.futures.algorithm45 import FMAlgorithm45
from wookitem import Item, FuturesItem, Order, OrderStatus
from wookdata import *
import math, copy, time

class Trader(TraderBase):
    def __init__(self, log, key):
        self.broker = Kiwoom(self, log, key)
        # self.broker = Bankis(self, log, key)
        self.algorithm = FMAlgorithm45(self, log)
        self.general_account_index = 0
        self.futures_account_index = 0
        super().__init__(log)

        # Initial work
        self.connect_broker()
        self.get_account_list()

        # Initial Values
        self.sb_capital.setValue(60000000)
        self.sb_interval.setValue(0.05)
        self.sb_loss_cut.setValue(0.20)
        self.sb_fee.setValue(0.003)
        self.sb_min_transaction.setValue(10)
        self.sb_amount.setValue(1)

        # Init Fields
        self.interval = self.sb_interval.value()
        self.loss_cut = self.sb_loss_cut.value()

        # Regression
        self.polynomial_features1 = PolynomialFeatures(degree=1, include_bias=False)
        self.polynomial_features2 = PolynomialFeatures(degree=2, include_bias=False)
        self.polynomial_features3 = PolynomialFeatures(degree=3, include_bias=False)
        self.linear_regression = LinearRegression()
        self.par1_slope_interval = 4
        self.r1_interval = 5
        self.r3_interval = 9

        # Test setup
        self.opening = True
        self.cbb_item_name.setCurrentIndex(4)
        self.broker.request_order_history()
        # self.algorithm.strangle_strategy = False
        # self.le_test.setText('One way')
        # self.le_test.setText('Strangle')

    def test1(self):
        self.debug('test1 button clicked')

        item_code = self.cbb_item_code.currentText()
        # self.broker.request_stock_price_min(item_code)
        self.broker.request_stock_price_min('122630')
        print('before')
        self.broker.event_loop.exec()
        print('after')


        self.broker.request_stock_price_min('048260')
        # requester = Requester(self.broker.request_stock_price_min, '122630')
        # requester.start()

        # print(self.broker.chart_prices[KOSPI200_CODE])
        # print(self.broker.chart_prices['122630'])

    def test2(self):
        self.debug('test2 button clicked')

        # print(self.broker.chart_prices['101S3000'])
        self.broker.request_stock_price_min('048260')

    def portfolio_acquired(self):
        if self.opening:
            self.opening = False
            self.broker.settle_up()

    def connect_broker(self):
        # if self.cb_auto_login.isChecked():
        #     self.broker.auto_login()
        # else:
        #     self.broker.login()
        #     self.broker.set_account_password()

        self.broker.auto_login()

    def get_account_list(self):
        account_list = self.broker.get_account_list()
        if account_list:
            self.cbb_account.addItems(self.broker.account_list)

        general_account_acquired = False
        futures_account_acquired = False
        for index, account in enumerate(account_list):
            if account[-2:] == KIWOOM_GENERAL_ACCOUNT_NUMBER_SUFFIX:
                self.general_account_index = index
                general_account_acquired = True
            elif account[-2:] == KIWOOM_FUTURES_ACCOUNT_NUMBER_SUFFIX:
                self.futures_account_index = index
                futures_account_acquired = True
            if general_account_acquired and futures_account_acquired:
                break

    def get_deposit(self):
        if self.running_futures_account():
            self.broker.request_futures_deposit_info()
        else:
            self.broker.request_deposit_info()

    def get_portfolio(self):
        if self.running_futures_account():
            self.broker.request_futures_portfolio_info()
        else:
            self.broker.request_portfolio_info()

    def get_order_history(self):
        self.broker.request_order_history()

    def go_chart(self):
        if self.algorithm.is_running:
            return

        self.chart_item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        self.broker.chart_prices.clear()
        self.chart = self.chart[0:0]
        self.chart_locator = list()
        self.chart_formatter = list()
        self.interval_prices = list()
        self.loss_cut_prices = list()
        self.top_price = 0
        self.bottom_price = 0

        if self.chart_item_code in self.broker.chart_prices:
            self.broker.chart_prices[self.chart_item_code].clear()

        if self.chart_item_code[:3] == FUTURES_CODE:
            self.broker.request_futures_stock_price_min(self.chart_item_code)
        elif self.chart_item_code[:3] == KOSPI200_CODE:
            self.broker.request_kospi200_index()
        else:
            self.broker.request_stock_price_min(self.chart_item_code)

        self.broker.is_running_chart = True
        self.timer.start()
        self.on_add_item()
        self.info('Go Charting', item_name)

    def stop_chart(self):
        self.broker.is_running_chart = False
        self.timer.stop()
        self.info('Stop Charting')

    def send_order(self):
        item_code = self.cbb_item_code.currentText()
        order_position = self.cbb_order_position.currentText()
        price = self.sb_price.value()
        amount = self.sb_amount.value()
        order_type = self.cbb_order_type.currentText()
        order_number = self.le_order_number.text()

        self.broker.order(item_code, price, amount, order_position, order_type, order_number)

    def update_deposit_info(self):
        if not self.broker.deposit or not self.broker.orderable_money:
            self.debug('No deposit information')
            return

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
        if item.current_price != 0 and type(self.broker.orderable_money) != str:
            buyable_amount = self.formalize(self.broker.orderable_money // item.current_price)
        self.lb_buyable.setText(buyable_amount)
        self.lb_sellable.setText(self.formalize(item.holding_amount))
        self.sb_price.setValue(item.current_price)

    def go(self):
        if self.algorithm.is_running:
            self.debug('Algorithm is already running')
            return

        capital = self.sb_capital.value()
        interval = self.sb_interval.value()
        loss_cut = self.sb_loss_cut.value()
        fee = self.sb_fee.value()
        minimum_transaction_amount = self.sb_min_transaction.value()
        self.algorithm.start(self.broker, capital, interval, loss_cut, fee, minimum_transaction_amount)
        self.log_info('Algorithm started')

    def stop(self):
        self.algorithm.stop()
        self.log_info('Algorithm stopped')

    def display_portfolio(self):
        self.clear_table(self.table_portfolio)
        for item in self.broker.portfolio.values():
            self.table_portfolio.insertRow(0)
            self.table_portfolio.setRowHeight(0, 8)
            self.table_portfolio.setItem(0, 0, self.to_item(item.item_name))
            self.table_portfolio.setItem(0, 1, self.to_item_float2(item.current_price))
            self.table_portfolio.setItem(0, 2, self.to_item_float3(item.purchase_price))
            self.table_portfolio.setItem(0, 3, self.to_item_sign(item.holding_amount))
            self.table_portfolio.setItem(0, 4, self.to_item(item.purchase_sum))
            self.table_portfolio.setItem(0, 5, self.to_item(item.evaluation_sum))
            self.table_portfolio.setItem(0, 6, self.to_item(item.total_fee))
            self.table_portfolio.setItem(0, 7, self.to_item(item.tax))
            self.table_portfolio.setItem(0, 8, self.to_item_sign(item.profit))
            self.table_portfolio.setItem(0, 9, self.to_item_sign(item.profit_rate))
            if isinstance(item, FuturesItem):
                self.display_futures_portfolio(item)
        self.table_portfolio.sortItems(0, Qt.AscendingOrder)

    def display_futures_portfolio(self, futures_item):
        for index, contract in enumerate(futures_item.contracts):
            self.table_portfolio.insertRow(0)
            self.table_portfolio.setRowHeight(0, 8)
            self.table_portfolio.setItem(0, 0, self.to_item_gray(contract.item_name + ' ({})'.format(index)))
            self.table_portfolio.setItem(0, 1, self.to_item_float2(contract.current_price))
            self.table_portfolio.setItem(0, 2, self.to_item_float2(contract.purchase_price))
            self.table_portfolio.setItem(0, 3, self.to_item_sign(contract.holding_amount))
            self.table_portfolio.setItem(0, 4, self.to_item(contract.purchase_sum))
            self.table_portfolio.setItem(0, 5, self.to_item(contract.evaluation_sum))
            self.table_portfolio.setItem(0, 6, self.to_item(contract.total_fee))
            self.table_portfolio.setItem(0, 7, self.to_item(contract.tax))
            self.table_portfolio.setItem(0, 8, self.to_item_sign(contract.profit))
            self.table_portfolio.setItem(0, 9, self.to_item_sign(contract.profit_rate))

    def display_monitoring_items(self):
        self.clear_table(self.table_monitoring_items)
        for item in self.broker.monitoring_items.values():
            self.table_monitoring_items.insertRow(0)
            self.table_monitoring_items.setRowHeight(0, 8)
            self.table_monitoring_items.setItem(0, 0, self.to_item(item.item_name))
            self.table_monitoring_items.setItem(0, 1, self.to_item_time(item.transaction_time))
            self.table_monitoring_items.setItem(0, 2, self.to_item_float2(item.current_price))
            self.table_monitoring_items.setItem(0, 3, self.to_item_float2(item.ask_price))
            self.table_monitoring_items.setItem(0, 4, self.to_item_float2(item.bid_price))
            self.table_monitoring_items.setItem(0, 5, self.to_item(item.volume))
            self.table_monitoring_items.setItem(0, 6, self.to_item(item.accumulated_volume))
            self.table_monitoring_items.setItem(0, 7, self.to_item_float2(item.high_price))
            self.table_monitoring_items.setItem(0, 8, self.to_item_float2(item.low_price))
            self.table_monitoring_items.setItem(0, 9, self.to_item_float2(item.open_price))
        self.table_monitoring_items.sortItems(0, Qt.DescendingOrder)

    def display_balance(self):
        self.clear_table(self.table_balance)
        for item in self.broker.balance.values():
            self.table_balance.insertRow(0)
            self.table_balance.setRowHeight(0, 8)
            self.table_balance.setItem(0, 0, self.to_item(item.item_name))
            self.table_balance.setItem(0, 1, self.to_item_float2(item.current_price))
            self.table_balance.setItem(0, 2, self.to_item_float2(item.reference_price))
            self.table_balance.setItem(0, 3, self.to_item(item.purchase_price_avg))
            self.table_balance.setItem(0, 4, self.to_item(item.holding_amount))
            self.table_balance.setItem(0, 5, self.to_item(item.purchase_sum))
            self.table_balance.setItem(0, 6, self.to_item_sign(item.purchase_amount_net_today))
            self.table_balance.setItem(0, 7, self.to_item_sign(item.balance_profit_net_today))
            self.table_balance.setItem(0, 8, self.to_item_sign(item.balance_profit_rate))
            self.table_balance.setItem(0, 9, self.to_item_sign(item.balance_profit_realization))
        self.table_balance.sortItems(0, Qt.DescendingOrder)

    def display_open_orders(self):
        self.clear_table(self.table_open_orders)
        for order in self.broker.open_orders.values():
            self.table_open_orders.insertRow(0)
            self.table_open_orders.setRowHeight(0, 8)
            self.table_open_orders.setItem(0, 0, self.to_item(order.item_name))
            self.table_open_orders.setItem(0, 1, self.to_item_time(order.executed_time))
            self.table_open_orders.setItem(0, 2, self.to_item(order.order_amount))
            self.table_open_orders.setItem(0, 3, self.to_item(order.executed_amount_sum))
            self.table_open_orders.setItem(0, 4, self.to_item(order.open_amount))
            self.table_open_orders.setItem(0, 5, self.to_item_plain(order.order_number))
            self.table_open_orders.setItem(0, 6, self.to_item_plain(order.original_order_number))
            self.table_open_orders.setItem(0, 7, self.to_item_float2(order.order_price))
            self.table_open_orders.setItem(0, 8, self.to_item(order.executed_price_avg))
            self.table_open_orders.setItem(0, 9, self.to_item_center(order.order_position))
            self.table_open_orders.setItem(0, 10, self.to_item_center(order.order_state))
        self.table_open_orders.sortItems(1, Qt.DescendingOrder)

    def display_order_history(self):
        history_count = len(self.broker.order_history)
        row_count = self.table_order_history.rowCount()
        index = row_count - history_count
        if not index: return

        order_history = list(self.broker.order_history.values())
        for order in order_history[index:]:
            self.table_order_history.insertRow(0)
            self.table_order_history.setRowHeight(0, 8)
            self.table_order_history.setItem(0, 0, self.to_item(order.item_name))
            self.table_order_history.setItem(0, 1, self.to_item_time(order.executed_time))
            self.table_order_history.setItem(0, 2, self.to_item(order.order_amount))
            self.table_order_history.setItem(0, 3, self.to_item(order.executed_amount_sum))
            self.table_order_history.setItem(0, 4, self.to_item(order.open_amount))
            self.table_order_history.setItem(0, 5, self.to_item_plain(order.order_number))
            self.table_order_history.setItem(0, 6, self.to_item_plain(order.original_order_number))
            self.table_order_history.setItem(0, 7, self.to_item_float2(order.order_price))
            self.table_order_history.setItem(0, 8, self.to_item_float2(order.executed_price_avg))
            self.table_order_history.setItem(0, 9, self.to_item_center(order.order_position))
            self.table_order_history.setItem(0, 10, self.to_item_center(order.order_state))
        # self.table_order_history.sortItems(1, Qt.DescendingOrder)

    def display_algorithm_trading(self):
        episodes = list(self.algorithm.episodes.values())
        episodes_count = len(episodes)
        positions_count = len(self.algorithm.positions)
        algorithm_count = episodes_count + positions_count
        row_count = self.table_algorithm_trading.rowCount()
        new_episode = algorithm_count - row_count
        removal_count = 6 - new_episode
        removal_count = row_count if removal_count > row_count else removal_count

        for index in range(removal_count):
            self.table_algorithm_trading.removeRow(0)

        self.insert_table_algorithm_trading(episodes[-4:])
        sorted_positions_list = sorted(self.algorithm.positions.items())
        sorted_positions = dict(sorted_positions_list)
        self.insert_table_algorithm_trading(sorted_positions.values())
        # self.table_algorithm_trading.sortItems(2, Qt.DescendingOrder)

        row_count = self.table_algorithm_trading.rowCount()
        if algorithm_count != row_count:
            self.clear_table(self.table_algorithm_trading)
            self.insert_table_algorithm_trading(episodes)
            sorted_positions_list = sorted(self.algorithm.positions.items())
            sorted_positions = dict(sorted_positions_list)
            self.insert_table_algorithm_trading(sorted_positions.values())

    def insert_table_algorithm_trading(self, data):
        for order in data:
            self.table_algorithm_trading.insertRow(0)
            self.table_algorithm_trading.setRowHeight(0, 8)
            self.table_algorithm_trading.setItem(0, 0, self.to_item(order.item_name))
            self.table_algorithm_trading.setItem(0, 1, self.to_item_time(order.executed_time))
            self.table_algorithm_trading.setItem(0, 2, self.to_item_plain(order.episode_number))
            self.table_algorithm_trading.setItem(0, 3, self.to_item_plain(order.order_number))
            self.table_algorithm_trading.setItem(0, 4, self.to_item_center(order.order_position))
            self.table_algorithm_trading.setItem(0, 5, self.to_item_center(order.order_state))
            self.table_algorithm_trading.setItem(0, 6, self.to_item_float2(order.order_price))
            self.table_algorithm_trading.setItem(0, 7, self.to_item_float2(order.executed_price_avg))
            self.table_algorithm_trading.setItem(0, 8, self.to_item(order.order_amount))
            self.table_algorithm_trading.setItem(0, 9, self.to_item(order.executed_amount_sum))
            self.table_algorithm_trading.setItem(0, 10, self.to_item_sign(order.open_amount))
            self.table_algorithm_trading.setItem(0, 11, self.to_item_sign(order.net_profit))

    def display_algorithm_trading_deprecated(self):
        self.clear_table(self.table_algorithm_trading)
        for algorithm_number, order in self.algorithm.episodes.items():
            self.table_algorithm_trading.insertRow(0)
            self.table_algorithm_trading.setRowHeight(0, 8)
            self.table_algorithm_trading.setItem(0, 0, self.to_item(order.item_name))
            self.table_algorithm_trading.setItem(0, 1, self.to_item_time(order.executed_time))
            self.table_algorithm_trading.setItem(0, 2, self.to_item_plain(order.episode_number))
            self.table_algorithm_trading.setItem(0, 3, self.to_item_plain(order.order_number))
            self.table_algorithm_trading.setItem(0, 4, self.to_item_center(order.order_position))
            self.table_algorithm_trading.setItem(0, 5, self.to_item_center(order.order_state))
            self.table_algorithm_trading.setItem(0, 6, self.to_item_float2(order.order_price))
            self.table_algorithm_trading.setItem(0, 7, self.to_item_float2(order.executed_price_avg))
            self.table_algorithm_trading.setItem(0, 8, self.to_item(order.order_amount))
            self.table_algorithm_trading.setItem(0, 9, self.to_item(order.executed_amount_sum))
            self.table_algorithm_trading.setItem(0, 10, self.to_item_sign(order.open_amount))
            self.table_algorithm_trading.setItem(0, 11, self.to_item_sign(order.net_profit))
        self.table_algorithm_trading.sortItems(2, Qt.DescendingOrder)

    def clear_table(self, table):
        for row in range(table.rowCount()):
            table.removeRow(0)

    def display_algorithm_results(self):
        total_profit = self.algorithm.total_profit
        formalized_profit = self.formalize(total_profit)
        profit_rate = round(total_profit / self.sb_capital.value() * 100, 2)
        profit_display = '{} ({}%)'.format(formalized_profit, profit_rate)
        self.lb_total_profit.setText(profit_display)

        total_fee = self.algorithm.total_fee
        formalized_fee = self.formalize(total_fee)
        self.lb_total_fee.setText(formalized_fee)

        net_profit = self.algorithm.net_profit
        formalized_net_profit = self.formalize(net_profit)
        net_profit_rate = round(net_profit / self.sb_capital.value() * 100, 2)
        net_profit_display = '{} ({}%)'.format(formalized_net_profit, net_profit_rate)
        self.lb_net_profit.setText(net_profit_display)

    def process_past_chart_prices(self, item_code, chart_prices):
        if self.algorithm.is_running:
            self.algorithm.process_past_chart_prices(item_code, chart_prices)
            return
        elif item_code != self.chart_item_code:
            return

        columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        past_chart = pandas.DataFrame(chart_prices, columns=columns)
        past_chart.Time = pandas.to_datetime(past_chart.Time)
        past_chart.set_index('Time', inplace=True)
        # self.chart = past_chart.append(self.chart)
        self.chart = past_chart

        # Moving average
        chart = self.chart
        chart['MA5'] = chart.Close.rolling(5, 1).mean().apply(lambda x: round(x, 3))
        chart['MA10'] = chart.Close.rolling(10, 1).mean().apply(lambda x: round(x, 3))
        chart['MA20'] = chart.Close.rolling(20, 1).mean().apply(lambda x: round(x, 3))

        chart['Diff5'] = chart.MA5.diff().fillna(0).apply(lambda x: round(x, 3))
        chart['Diff10'] = chart.MA10.diff().fillna(0).apply(lambda x: round(x, 3))
        chart['Diff20'] = chart.MA20.diff().fillna(0).apply(lambda x: round(x, 3))
        chart['DiffDiff5'] = chart.Diff5.diff().fillna(0).apply(lambda x: round(x, 3))
        chart['DiffDiff10'] = chart.Diff10.diff().fillna(0).apply(lambda x: round(x, 3))
        chart['DiffDiff20'] = chart.Diff20.diff().fillna(0).apply(lambda x: round(x, 3))
        chart['PA'] = round((chart.High + chart.Low) / 2, 3)
        chart[['X1', 'PAR1', 'PAR1_Slope', 'PAR1_SlopeSlope', 'BL', 'SL', 'LLL', 'ULL']] = 0
        chart[['X3', 'PAR3', 'PAR3_Diff', 'PAR3_DiffDiff', 'PAR3_DiffDiffDiff']] = 0
        chart[['MA5R3', 'MA5R3_Diff', 'MA5R3_DiffDiff', 'MA5R3_DiffDiffDiff']] = 0

        x1, PAR1 = self.get_linear_regression(chart, chart.PA, self.r1_interval)
        x3, PAR3 = self.get_cubic_regression(chart, chart.PA, self.r3_interval)
        x3, MA5R3 = self.get_cubic_regression(chart, chart.MA5, self.r3_interval)

        chart_len = len(chart)
        x1_len = self.r1_interval
        if chart_len < self.r1_interval:
            x1_len = chart_len
        x1_interval = chart.index[-x1_len:]
        x3_len = self.r3_interval
        if chart_len < self.r3_interval:
            x3_len = chart_len
        x3_interval = chart.index[-x3_len:]

        PAR1_Slope = np.polyfit(x1, PAR1, 1)[0]
        chart.loc[x1_interval, 'X1'] = x1
        chart.loc[x1_interval, 'PAR1_Slope'] = PAR1_Slope

        x_slope_interval = chart.index[-self.par1_slope_interval:]
        x_slopeslope = chart.loc[x_slope_interval, 'X1']
        y_slopeslope = chart.loc[x_slope_interval, 'PAR1_Slope']
        PAR1_SlopeSlope = np.polyfit(x_slopeslope, y_slopeslope, 1)[0]

        chart.loc[x1_interval, 'PAR1'] = PAR1
        chart.loc[x1_interval, 'BL'] = PAR1 - self.interval
        chart.loc[x1_interval, 'SL'] = PAR1 + self.interval
        chart.loc[x1_interval, 'LLL'] = PAR1 - self.loss_cut
        chart.loc[x1_interval, 'ULL'] = PAR1 + self.loss_cut
        chart.loc[x1_interval, 'PAR1_SlopeSlope'] = PAR1_SlopeSlope
        chart.loc[x3_interval, 'X3'] = x3
        chart.loc[x3_interval, 'PAR3'] = PAR3
        chart.loc[x3_interval, 'PAR3_Diff'] = chart.PAR3.diff().fillna(0)
        chart.loc[x3_interval, 'PAR3_DiffDiff'] = chart.PAR3_Diff.diff().fillna(0)
        chart.loc[x3_interval, 'PAR3_DiffDiffDiff'] = chart.PAR3_DiffDiff.diff().fillna(0)
        chart.loc[x3_interval, 'MAR3'] = MA5R3
        chart.loc[x3_interval, 'MAR3_Diff'] = chart.MAR3.diff().fillna(0)
        chart.loc[x3_interval, 'MAR3_DiffDiff'] = chart.MAR3_Diff.diff().fillna(0)
        chart.loc[x3_interval, 'MAR3_DiffDiffDiff'] = chart.MAR3_DiffDiff.diff().fillna(0)

        self.draw_chart.start()

    def update_chart_prices(self, price, volume, item_code):
        if item_code != self.chart_item_code:
            return

        current_time = datetime.now().replace(second=0, microsecond=0)
        chart = self.chart
        if not len(chart):
            chart.loc[current_time] = price
            chart.loc[current_time, 'Volume'] = volume
        elif current_time > chart.index[-1]:
            chart.loc[current_time] = price
            chart.loc[current_time, 'Volume'] = volume
        else:
            if price > chart.High[-1]:
                chart.loc[current_time, 'High'] = price
            elif price < chart.Low[-1]:
                chart.loc[current_time, 'Low'] = price
            last_price = chart.Close[-1]
            chart.loc[current_time, 'Close'] = price
            chart.loc[current_time, 'Volume'] += volume
            if last_price == price:
                return

        # Moving average
        chart_len = len(self.chart)
        ma5 = -5
        ma10 = -10
        ma20 = -20
        if chart_len < 5:
            ma5 = chart_len * -1
            ma10 = chart_len * -1
            ma20 = chart_len * -1
        elif chart_len < 10:
            ma10 = chart_len * -1
            ma20 = chart_len * -1
        elif chart_len < 20:
            ma20 = chart_len * -1
        chart = self.chart
        chart.loc[current_time, 'MA5'] = round(chart.Close[ma5:].mean(), 3)
        chart.loc[current_time, 'MA10'] = round(chart.Close[ma10:].mean(), 3)
        chart.loc[current_time, 'MA20'] = round(chart.Close[ma20:].mean(), 3)

        chart.loc[current_time, 'Diff5'] = round(chart.MA5[-1] - chart.MA5[-2], 3)
        chart.loc[current_time, 'Diff10'] = round(chart.MA10[-1] - chart.MA10[-2], 3)
        chart.loc[current_time, 'Diff20'] = round(chart.MA20[-1] - chart.MA20[-2], 3)
        chart.loc[current_time, 'DiffDiff5'] = round(chart.Diff5[-1] - chart.Diff5[-2], 3)
        chart.loc[current_time, 'DiffDiff10'] = round(chart.Diff10[-1] - chart.Diff10[-2], 3)
        chart.loc[current_time, 'DiffDiff20'] = round(chart.Diff20[-1] - chart.Diff20[-2], 3)
        chart.loc[current_time, 'PA'] = round(((chart.High[-1] + chart.Low[-1]) / 2), 3)

        x1, PAR1 = self.get_linear_regression(chart, chart.PA, self.r1_interval)
        # x1, PAR1 = self.get_linear_regression(chart, chart.Close, self.r1_interval)
        x3, PAR3 = self.get_cubic_regression(chart, chart.PA, self.r3_interval)
        x3, MA5R3 = self.get_cubic_regression(chart, chart.MA5, self.r3_interval)

        chart_len = len(chart)
        x1_len = self.r1_interval
        x3_len = self.r3_interval
        if chart_len < self.r1_interval:
            x1_len = chart_len
        x1_interval = chart.index[-x1_len:]
        if chart_len < self.r3_interval:
            x3_len = chart_len
        x3_interval = chart.index[-x3_len:]

        PAR1_Slope = np.polyfit(x1, PAR1, 1)[0]
        chart.loc[x1_interval, 'X1'] = x1
        chart.loc[x1_interval, 'PAR1'] = PAR1

        chart.loc[x1_interval, 'BL'] = PAR1 - self.interval
        chart.loc[x1_interval, 'SL'] = PAR1 + self.interval
        chart.loc[x1_interval, 'LLL'] = PAR1 - self.loss_cut
        chart.loc[x1_interval, 'ULL'] = PAR1 + self.loss_cut

        x_slope_interval = chart.index[-self.par1_slope_interval:]
        x_slopeslope = chart.loc[x_slope_interval, 'X1']
        y_slopeslope = chart.loc[x_slope_interval, 'PAR1_Slope']
        PAR1_SlopeSlope = np.polyfit(x_slopeslope, y_slopeslope, 1)[0]

        chart.loc[chart.index[-1], 'PAR1_Slope'] = PAR1_Slope
        chart.loc[chart.index[-1], 'PAR1_SlopeSlope'] = PAR1_SlopeSlope
        chart.loc[x3_interval, 'X3'] = x3
        chart.loc[x3_interval, 'PAR3'] = PAR3
        chart.loc[x3_interval, 'PAR3_Diff'] = chart.PAR3.diff().fillna(0)
        chart.loc[x3_interval, 'PAR3_DiffDiff'] = chart.PAR3_Diff.diff().fillna(0)
        chart.loc[chart.index[-1], 'PAR3_DiffDiffDiff'] = chart.PAR3_DiffDiff[-1] - chart.PAR3_DiffDiff[-2]
        chart.loc[x3_interval, 'MAR3'] = MA5R3
        chart.loc[x3_interval, 'MAR3_Diff'] = chart.MAR3.diff().fillna(0)
        chart.loc[x3_interval, 'MAR3_DiffDiff'] = chart.MAR3_Diff.diff().fillna(0)
        chart.loc[chart.index[-1], 'MAR3_DiffDiffDiff'] = chart.MAR3_DiffDiff[-1] - chart.MAR3_DiffDiff[-2]

        self.draw_chart.start()

    def on_every_minute(self):
        current_time = datetime.now().replace(second=0, microsecond=0)
        if not len(self.chart):
            return
        if current_time > self.chart.index[-1]:
            price = self.chart.Close[-1]
            self.chart.loc[current_time] = price
            self.chart.loc[current_time, 'Volume'] = 0
            self.update_chart_prices(price, 0, self.chart_item_code)
            self.draw_chart.start()

    def display_chart(self):
        chart_len = len(self.chart)
        if not chart_len:
            return

        self.chart_ax.clear()

        # Set lim
        x2 = chart_len
        x1 = x2 - self.chart_scope
        if x1 < 0:
            x1 = 0
        elif x1 > x2 - 1:
            x1 = x2 - 1
        min_price = self.get_min_price(x1, x2)
        max_price = self.get_max_price(x1, x2)
        y1 = min_price - 0.1
        y2 = max_price + 0.1
        self.chart_ax.set_xlim(x1, x2)
        self.chart_ax.set_ylim(y1, y2)

        # Axis ticker formatting
        if chart_len // 30 > len(self.chart_locator) - 1:
            for index in range(len(self.chart_locator) * 30, len(self.chart), 30):
                time_format = self.chart.index[index].strftime('%H:%M')
                self.chart_locator.append(index)
                self.chart_formatter.append(time_format)
        self.chart_ax.xaxis.set_major_locator(ticker.FixedLocator(self.chart_locator))
        self.chart_ax.xaxis.set_major_formatter(ticker.FixedFormatter(self.chart_formatter))

        # Axis yticks & lines
        # max_price = self.chart.High.max()
        # min_price = self.chart.Low.min()
        # if max_price > self.top_price or min_price < self.bottom_price:
        #     self.top_price = math.ceil(max_price / self.interval) * self.interval
        #     self.bottom_price = math.floor(min_price / self.interval) * self.interval
        #     self.interval_prices = np.arange(self.bottom_price, self.top_price + self.interval, self.interval)
        #     self.loss_cut_prices = np.arange(self.bottom_price + self.interval - self.loss_cut, self.top_price, self.interval)
        # self.chart_ax.grid(axis='x', alpha=0.5)
        # self.chart_ax.set_yticks(self.interval_prices)
        # for price in self.interval_prices:
        #     self.chart_ax.axhline(price, alpha=0.5, linewidth=0.2)
        # for price in self.loss_cut_prices:
        #     self.chart_ax.axhline(price, alpha=0.4, linewidth=0.2, color='Gray')

        y_range = max_price - min_price
        hline_interval = wmath.get_nearest_top(y_range / 20)
        hline_interval = 0.05 if hline_interval < 0.05 else hline_interval
        hline_prices = np.arange(min_price, max_price, hline_interval)
        self.chart_ax.grid(axis='x', alpha=0.5)
        self.chart_ax.set_yticks(hline_prices)
        for price in hline_prices:
            self.chart_ax.axhline(price, alpha=0.5, linewidth=0.2)

        # Current Price Annotation
        current_time = len(self.chart)
        current_price = self.chart.Close.iloc[-1]
        if self.chart_item_code[:3] == FUTURES_CODE:
            formatted_current_price = format(current_price, ',.2f')
        else:
            formatted_current_price = format(current_price, ',')
        # self.ax.text(current_time + 2, current_price, format(current_price, ','))
        self.chart_ax.text(current_time + 2, current_price, formatted_current_price)

        # Moving average
        x = range(x1, x2)
        self.chart_ax.plot(x, self.chart.MA5[x1:x2], label='MA5', color='Magenta')
        self.chart_ax.plot(x, self.chart.MA10[x1:x2], label='MA10', color='RoyalBlue')
        self.chart_ax.plot(x, self.chart.MA20[x1:x2], label='MA20', color='Gold')
        self.chart_ax.legend(loc='best')

        # Regression
        x1_len = self.r1_interval
        x3_len = self.r3_interval
        if chart_len < x1_len:
            x1_len = chart_len
        if chart_len < x3_len:
            x3_len = chart_len

        self.chart_ax.plot(self.chart.X1[-x1_len:], self.chart.PAR1[-x1_len:], color='DarkOrange')
        # self.chart_ax.plot(chart.X3[-x3_len:], self.chart.PAR3[-x3_len:], color='Cyan')
        # self.self.chart_ax.plot(self.chart.X3[-x3_len:], self.chart.MAR3[-x3_len:], color='DarkSlateGray')
        self.chart_ax.plot(self.chart.X1[-x1_len:], self.chart.PAR1[-x1_len:] + self.loss_cut, color='Gray')
        self.chart_ax.plot(self.chart.X1[-x1_len:], self.chart.PAR1[-x1_len:] - self.loss_cut, color='Gray')
        self.chart_ax.plot(self.chart.X1[-x1_len:], self.chart.PAR1[-x1_len:] - self.interval, color='DarkGray')
        self.chart_ax.plot(self.chart.X1[-x1_len:], self.chart.PAR1[-x1_len:] + self.interval, color='DarkGray')

        # Draw Chart
        candlestick2_ohlc(self.chart_ax, self.chart.Open, self.chart.High, self.chart.Low, self.chart.Close,
                          width=0.4, colorup='red', colordown='blue')
        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def display_chart_plain(self):
        chart_len = len(self.chart)
        if not chart_len:
            return

        self.chart_ax.clear()

        # Axis ticker formatting
        if chart_len // 30 > len(self.chart_locator) - 1:
            for index in range(len(self.chart_locator) * 30, len(self.chart), 30):
                time_format = self.chart.index[index].strftime('%H:%M')
                self.chart_locator.append(index)
                self.chart_formatter.append(time_format)
        self.chart_ax.xaxis.set_major_locator(ticker.FixedLocator(self.chart_locator))
        self.chart_ax.xaxis.set_major_formatter(ticker.FixedFormatter(self.chart_formatter))

        # Axis yticks & lines
        max_price = self.chart.High.max()
        min_price = self.chart.Low.min()
        if max_price > self.top_price or min_price < self.bottom_price:
            self.top_price = math.ceil(max_price / self.interval) * self.interval
            self.bottom_price = math.floor(min_price / self.interval) * self.interval
            self.interval_prices = np.arange(self.bottom_price, self.top_price + self.interval, self.interval)
            self.loss_cut_prices = np.arange(self.bottom_price + self.interval - self.loss_cut, self.top_price, self.interval)
        self.chart_ax.grid(axis='x', alpha=0.5)
        self.chart_ax.set_yticks(self.interval_prices)
        for price in self.interval_prices:
            self.chart_ax.axhline(price, alpha=0.5, linewidth=0.2)
        for price in self.loss_cut_prices:
            self.chart_ax.axhline(price, alpha=0.4, linewidth=0.2, color='Gray')

        # Current Price Annotation
        current_time = len(self.chart)
        current_price = self.chart.Close.iloc[-1]
        if self.chart_item_code[:3] == FUTURES_CODE:
            formatted_current_price = format(current_price, ',.2f')
        else:
            formatted_current_price = format(current_price, ',')
        # self.ax.text(current_time + 2, current_price, format(current_price, ','))
        self.chart_ax.text(current_time + 2, current_price, formatted_current_price)

        # Moving average
        x = range(0, chart_len)
        self.chart_ax.plot(x, self.chart.MA5, label='MA5', color='Magenta')
        self.chart_ax.plot(x, self.chart.MA10, label='MA10', color='RoyalBlue')
        self.chart_ax.plot(x, self.chart.MA20, label='MA20', color='Gold')
        self.chart_ax.legend(loc='best')

        # Set lim
        x2 = chart_len
        x1 = x2 - self.chart_scope
        if x1 < 0:
            x1 = 0
        elif x1 > x2 - 1:
            x1 = x2 - 1
        y1 = self.chart.Low[x1:x2].min() - 0.1
        y2 = self.chart.High[x1:x2].max() + 0.1
        self.chart_ax.set_xlim(x1, x2)
        self.chart_ax.set_ylim(y1, y2)

        # Draw Chart
        candlestick2_ohlc(self.chart_ax, self.chart.Open, self.chart.High, self.chart.Low, self.chart.Close,
                          width=0.4, colorup='red', colordown='blue')
        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def on_select_account(self, index):
        self.broker.account_number = self.cbb_account.currentText()

        if index == self.futures_account_index:
            self.broker.request_futures_deposit_info()
            self.broker.request_futures_portfolio_info()
            # if not self.running_futures_code():
            #     self.cbb_item_code.setCurrentText('101')
        else:
            self.broker.request_deposit_info()
            self.broker.request_portfolio_info()
            # if self.running_futures_code():
            #     self.cbb_item_code.setCurrentText('')

    def on_select_item_code(self, item_code):
        item_name = CODES.get(item_code)
        if not item_name:
            item_name = self.broker.get_item_name(item_code)
            if item_name != '':
                CODES[item_code] = item_name
                self.cbb_item_code.addItem(item_code)
                self.cbb_item_name.addItem(item_name)

        if item_code[:3] == FUTURES_CODE:
            self.cbb_order_type.clear()
            self.cbb_order_type.addItems(FUTURES_ORDER_TYPE)
            self.cbb_account.setCurrentIndex(self.futures_account_index)
        else:
            self.cbb_order_type.clear()
            self.cbb_order_type.addItems(ORDER_TYPE)
            self.cbb_account.setCurrentIndex(self.general_account_index)

        self.cbb_item_name.setCurrentText(item_name)
        self.update_order_variables()

    def on_select_item_name(self, index):
        item_name = self.cbb_item_name.currentText()
        item_code = self.broker.get_item_code(item_name) if item_name != 'KOSPI200' else KOSPI200_CODE
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
        if item_name[:2] == 'F ':
            item_name = item_name[:8]
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 1
        current_price_item = self.table_portfolio.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

        holding_amount_column = 3
        holding_amount_item = self.table_portfolio.item(row, holding_amount_column)
        holding_amount = self.process_type(holding_amount_item.text())
        self.sb_amount.setValue(abs(holding_amount))

        self.cbb_order_type.setCurrentText('MARKET')
        if holding_amount > 0:
            self.cbb_order_position.setCurrentText('SELL')
        else:
            self.cbb_order_position.setCurrentText('BUY')

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
        open_amount = self.process_type(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

        order_number_column = 5
        order_number_item = self.table_open_orders.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 7
        order_price_item = self.table_open_orders.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

        order_position_column = 9
        order_position_item = self.table_open_orders.item(row, order_position_column)
        order_position = order_position_item.text()
        if order_position == PURCHASE[-2:]:
            self.cbb_order_position.setCurrentText('CANCEL BUY')
        elif order_position == SELL[-2:]:
            self.cbb_order_position.setCurrentText('CANCEL SELL')

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

        order_number_column = 3
        order_number_item = self.table_algorithm_trading.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 6
        order_price_item = self.table_algorithm_trading.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        if order_price:
            self.sb_price.setValue(order_price)

        open_amount_column = 10
        open_amount_item = self.table_algorithm_trading.item(row, open_amount_column)
        open_amount = self.process_type(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

    def get_regression(self, x, y, interval, predict_len, polynomial_features):
        if interval is None:
            interval = self.r3_interval

        x_len = len(x)
        if x_len < interval:
            interval = x_len

        x2 = x_len
        x1 = x2 - interval
        x3 = x2 + predict_len
        x_regression = np.arange(x1, x3)
        x_reshape = x_regression.reshape(-1, 1)
        x_fitted = polynomial_features.fit_transform(x_reshape)
        self.linear_regression.fit(x_fitted, y.values[x1:x2])
        y_regression = self.linear_regression.predict(x_fitted)

        return x_regression, y_regression

    def get_linear_regression(self, x, y, interval=None, predict_len=0):
        x_regression, y_regression = self.get_regression(x, y, interval, predict_len, self.polynomial_features1)
        return x_regression, y_regression

    def get_quadratic_regression(self, x, y, interval=None, predict_len=0):
        x_regression, y_regression = self.get_regression(x, y, interval, predict_len, self.polynomial_features2)
        return x_regression, y_regression

    def get_cubic_regression(self, x, y, interval=None, predict_len=0):
        x_regression, y_regression = self.get_regression(x, y, interval, predict_len, self.polynomial_features3)
        return x_regression, y_regression

    def get_max_price(self, x1, x2):
        max_price = self.chart.High[x1:x2].max()
        return max_price

    def get_min_price(self, x1, x2):
        min_price = self.chart.Low[x1:x2].min()
        return min_price

    def set_algorithm_parameters(self):
        self.interval = self.sb_interval.value()
        self.loss_cut = self.sb_loss_cut.value()
        self.algorithm.capital = self.sb_capital.value()
        self.algorithm.interval = self.interval
        self.algorithm.loss_cut = self.loss_cut
        self.algorithm.fee = self.sb_fee.value()
        self.algorithm.minimum_transaction_amount = self.sb_min_transaction.value()

    def on_edit_save_file(self):
        file = self.le_save_file.text()
        self.broker.log_file = file

    def on_change_save_file(self):
        file = QFileDialog.getOpenFileName(self, 'Select File', self.setting['save_folder'])[0]
        if file != '':
            self.le_save_file.setText(file)
            self.broker.log_file = file

    def running_futures_code(self):
        if self.cbb_item_code.currentText()[:3] == FUTURES_CODE:
            return True
        else:
            return False

    def running_futures_account(self):
        if self.cbb_account.currentIndex() == self.futures_account_index:
            return True
        else:
            return False

    def edit_setting(self):
        self.debug('setting')

    def log(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        current_time = datetime.now().strftime('%H:%M:%S') + ' '
        # self.te_info.append(current_time + message)
        self.info(message)

    def log_info(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        current_time = datetime.now().strftime('%H:%M:%S') + ' '
        # self.te_info.append(current_time + message)

    def status(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        self.status_bar.showMessage(message)

    def closeEvent(self, event):
        # self.broker.log('Closing process initializing...')
        self.broker.close_process()
        self.broker.clear()
        self.broker.deleteLater()
        # self.deleteLater()