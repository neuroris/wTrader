import numpy
from mplfinance.original_flavor import candlestick2_ohlc
from matplotlib import ticker
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from datetime import datetime
from wookitem import Order, Episode, AlgorithmItem, FuturesAlgorithmItem
from wookutil import wmath
from wookdata import *
from wookalgorithm.futuresalgorithmbase import FuturesAlgorithmBase
import pandas
import math, copy

'''
Original Algorithm (2021, 09, 13)
1. Price average first degree regression model
2. Dynamic volatility (no shift, moving loss cut) 
3. Limit order
4. Multiple episode
5. Concentrate on continuous automatic trading
6. Stable version for preservation
7. R1 interval modification by trend deviation
8. Only one position at a time
9. Dynamic settlement (immediate counter trade after settlement)
10. Open / Close position system could be deprecated
'''

class FMAlgorithm8(FuturesAlgorithmBase):
    def __init__(self, trader, log):
        super().__init__(trader, log)
        self.futures = None
        self.slope = None
        self.long_position_history = dict()
        self.short_position_history = dict()
        self.open_position_history = dict()
        self.close_position_history = dict()

        # Variables
        self.trading_halted = False
        self.default_r1_interval = 10
        self.margin_ratio = 0.15
        self.cancel_purchase_amount = 0
        self.cancel_sale_amount = 0
        self.cancel_margin = 0.00
        self.profit_rate_margin = -0.08
        self.trend_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        # Regression
        self.polynomial_features1 = PolynomialFeatures(degree=1, include_bias=False)
        self.polynomial_features2 = PolynomialFeatures(degree=2, include_bias=False)
        self.polynomial_features3 = PolynomialFeatures(degree=3, include_bias=False)
        self.linear_regression = LinearRegression()
        self.r1_interval = self.default_r1_interval
        self.r3_interval = 9
        self.par1_slope_interval = 4

    def start(self, broker, capital, interval, loss_cut, fee, minimum_transaction_amount):
        self.futures = FuturesAlgorithmItem('101RC000')
        self.add_item(self.futures)
        self.initialize(broker, capital, interval, loss_cut, fee, minimum_transaction_amount)

        # Open Orders cancellation
        self.clear_open_orders()

        # Charting & Monitoring
        broker.chart_prices.clear()
        broker.request_futures_stock_price_min(self.futures.item_code)
        broker.demand_monitoring_items_info(self.futures)
        self.timer.start()
        self.is_running = True
        self.post('STARTED')

    def market_status(self, item):
        if not self.start_time:
            self.start_work(item.current_price)

        # Update chart
        self.set_r1_interval()
        self.update_chart_prices(item.item_code, item.current_price, item.volume)

        if self.trading_halted:
            return

        if self.work_in_progress():
            return

        self.futures.update_profit(item.current_price)
        self.post_without_repetition('(DEBUG)', 'profit', self.futures.profit, 'profit rate', self.futures.profit_rate)

        self.monitor_trend_deviation(item.current_price)
        self.correct_order_prices(item.current_price)

    def start_work(self, current_price):
        now = datetime.now()
        self.start_time_text = now.strftime('%H:%M')
        self.start_time = self.to_min_count(self.start_time_text)
        self.start_price = current_price
        self.start_comment = 'start\n' + self.start_time_text + '\n' + format(self.start_price, ',')
        self.episode_amount = int((self.capital / self.margin_ratio) // (current_price * MULTIPLIER))
        self.initiate_order()

    def initiate_order(self, amount=0, price=0, order_type='LIMIT'):
        self.trade_by_trend(amount, price, order_type)

    def trade_by_trend(self, amount=0, price=0, order_type='LIMIT'):
        if self.futures.chart.PAR1_Slope[-1] >= 0:
            self.buy(amount, price, order_type)
        else:
            self.sell(amount, price, order_type)

    def set_r1_interval(self):
        now = datetime.now().replace(second=0, microsecond=0)
        interval = now - self.trend_start
        if interval.seconds < (self.default_r1_interval - 1) * 60:
            self.r1_interval = interval.seconds // 60 + 2
            self.post_magenta('R1 interval', self.r1_interval)

    def monitor_trend_deviation(self, current_price):
        if self.futures.profit_rate < self.profit_rate_margin:
            self.post_magenta('(MONITOR)', 'Too Much Loss!!')
            # self.trend_start = datetime.now().replace(second=0, microsecond=0)
            # self.halt_trading()
        elif current_price > self.futures.chart.ULL[-1]:
            self.post_magenta('(MONITOR)', 'Above Upper Loss Limit!!')
            # self.trend_start = datetime.now().replace(second=0, microsecond=0)
            # self.halt_trading()
        elif current_price < self.futures.chart.LLL[-1]:
            self.post_magenta('(MONITOR)', 'Below Lower Loss Limint!!')
            # self.trend_start = datetime.now().replace(second=0, microsecond=0)
            # self.halt_trading()

    def halt_trading(self):
        if self.trading_halted:
            return

        self.post('Trading halt!!!!!!!')
        self.trading_halted = True
        self.clear_open_orders()
        self.open_purchase_orders = 0
        self.open_sale_orders = 0
        self.open_purchase_correct_orders = 0
        self.open_sale_correct_orders = 0
        self.open_purchase_cancel_orders = 0
        self.open_sale_cancel_orders = 0
        self.cancel_purchase_amount = 0
        self.cancel_sale_amount = 0
        self.long_position.order_amount = self.long_position.executed_amount_sum
        self.short_position.order_amount = self.short_position.executed_amount_sum

    def resume_trading(self):
        if not self.trading_halted:
            return

        self.post('Trading resumes')
        self.trading_halted = False
        buy_amount = self.episode_amount - self.futures.holding_amount
        sell_amount = self.futures.holding_amount + self.episode_amount
        if buy_amount:
            self.buy(buy_amount)
        if sell_amount:
            self.sell(sell_amount)

    def work_in_progress(self):
        if self.open_purchase_orders:
            self.post('(BLOCK)', 'purchase ordered', self.open_purchase_orders)
            return True
        elif self.open_sale_orders:
            self.post('(BLOCK)', 'sale ordered', self.open_sale_orders)
            return True
        elif self.open_purchase_correct_orders:
            self.post('(BLOCK)', 'open purchase correct orders', self.open_purchase_correct_orders)
            return True
        elif self.open_sale_correct_orders:
            self.post('(BLOCK)', 'open sale correct orders', self.open_sale_correct_orders)
            return True
        elif self.open_purchase_cancel_orders:
            self.post('(BLOCK)', 'open purchase cancel orders', self.open_purchase_cancel_orders)
            return True
        elif self.open_sale_cancel_orders:
            self.post('(BLOCK)', 'open sale cancel orders', self.open_sale_cancel_orders)
            return True
        elif self.open_cancel_orders:
            self.post('(BLOCK)', 'open cancel orders', self.open_cancel_orders)
            return True
        elif self.stop_loss_ordered:
            self.post_without_repetition('(BLOCK)', 'stop loss ordered')
            return True
        elif self.time_off_in_progress:
            self.post_without_repetition('(BLOCK)', 'time off')
            return True
        elif self.settle_up_in_progress:
            self.post_without_repetition('(BLOCK)', 'settle up in progress')
            return True
        elif self.finish_up_in_progress:
            self.post_without_repetition('(BLOCK)', 'finish in progress')
            return True
        else:
            return False

    def buy(self, amount=0, price=0, order_type='LIMIT'):
        self.open_purchase_orders += 1
        self.post('(ORDER)', 'purchase order LOCKED', self.open_purchase_orders)
        price = price if price else self.get_buy_limit()
        amount = amount if amount else self.episode_amount
        self.futures.buy(price, amount, order_type)

    def sell(self, amount=0, price=0, order_type='LIMIT'):
        self.open_sale_orders += 1
        self.post('(ORDER)', 'sale order LOCKED', self.open_sale_orders)
        price = price if price else self.get_sell_limit()
        amount = amount if amount else self.episode_amount
        self.futures.sell(price, amount, order_type)

    def counter_trade(self, order):
        self.post('(ORDER)', 'counter trade')
        executed_amount = abs(order.executed_amount)
        if order.order_position in PURCHASE_EQUIVALENT:
            self.sell(executed_amount)
        elif order.order_position in SELL_EQUIVALENT:
            self.buy(executed_amount)

    def clear_up_holdings(self):
        self.post('CLEAR UP HOLDINGS!!!!!!')
        if self.futures.holding_amount > 0:
            self.futures.sell_off()
        elif self.futures.holding_amount < 0:
            self.futures.buy_off()

    def correct_order_prices_deprecated(self, current_price):
        if self.futures.purchases and not (self.futures.holding_amount > 0):
            buy_limit = self.get_buy_limit()
            if self.long_position.order_price != buy_limit:
                if abs(current_price - buy_limit) > self.cancel_margin:
                    self.open_purchase_cancel_orders = len(self.futures.purchases)
                    self.cancel_purchases_ordered = True
                    self.post('(CORRECT)', 'purchase orders!!', self.open_purchase_cancel_orders)
                    self.futures.cancel_purchases()
        elif self.futures.sales and not (self.futures.holding_amount < 0):
            sell_limit = self.get_sell_limit()
            if self.short_position.order_price != sell_limit:
                if abs(current_price - sell_limit) > self.cancel_margin:
                    self.open_sale_cancel_orders = len(self.futures.sales)
                    self.cancel_sales_ordered = True
                    self.post('(CORRECT)', 'sale orders!!', self.open_sale_cancel_orders)
                    self.futures.cancel_sales()

    def correct_order_prices(self, current_price):
        if self.futures.purchases and not (self.futures.holding_amount > 0):
            buy_limit = self.get_buy_limit()
            if self.long_position.order_price != buy_limit:
                if abs(current_price - buy_limit) > self.cancel_margin:
                    self.open_purchase_correct_orders = len(self.futures.purchases)
                    self.correct_purchases_ordered = True
                    self.post('(CORRECT)', 'purchase orders!!', self.open_purchase_correct_orders)
                    self.futures.correct_purchases(buy_limit)
        elif self.futures.sales and not (self.futures.holding_amount < 0):
            sell_limit = self.get_sell_limit()
            if self.short_position.order_price != sell_limit:
                if abs(current_price - sell_limit) > self.cancel_margin:
                    self.open_sale_correct_orders = len(self.futures.sales)
                    self.correct_sales_ordered = True
                    self.post('(CORRECT)', 'sale orders!!', self.open_sale_correct_orders)
                    self.futures.correct_sales(sell_limit)

    def update_execution_info(self, order):
        self.post_cyan('(EXECUTION1)', 'holding', self.futures.holding_amount,
                       'virtual', self.futures.virtual_holding_amount,
                       'order.executed_amount', order.executed_amount)

        # Update Algorithm item orders
        self.futures.update_orders(order)

        # Update algorithm item contracts
        if order.executed_amount:
            if self.futures.holding_amount * order.executed_amount >= 0:
                self.post_blue('Add contract called')
                self.futures.add_contract(order)
            else:
                self.post_blue('Settle contract called')
                self.futures.settle_contracts(order)

        # Update long & short position episodes
        if order.order_position in (PURCHASE, CORRECT_PURCHASE):
            self.update_long_position(order)
        elif order.order_position in (SELL, CORRECT_SELL):
            self.update_short_position(order)

        # Update open & close position episodes
        # if not self.futures.virtual_holding_amount:
        #     self.update_open_position(order)
        # elif self.open_position.is_equivalent(order.order_position):
        #     self.update_open_position(order)
        # elif self.open_position.is_opposite(order.order_position):
        #     self.update_close_position(order)
        if self.futures.virtual_holding_amount * order.position_sign() >= 0:
            self.update_open_position(order)
        else:
            self.update_close_position(order)

        self.post_cyan('(EXECUTION2)', 'holding', self.futures.holding_amount,
                       'virtual', self.futures.virtual_holding_amount)

        # Order processing
        if self.trading_halted:
            self.count_clear_orders(order)
        else:
            self.subsequent_orders(order)
            self.count_open_orders(order)

        # Display
        self.post_order_details(order)
        self.trader.display_algorithm_trading()
        self.trader.display_algorithm_results()
        self.draw_chart.start()

    def update_long_position(self, order):
        executed_amount = abs(order.executed_amount)
        self.long_position.episode_number = 'LP'
        self.long_position.item_name = order.item_name
        self.episodes[self.long_position.episode_number] = self.long_position
        self.long_position.order_price = order.order_price
        self.long_position.executed_time = order.executed_time
        self.long_position.order_number = order.order_number
        self.long_position.order_position = order.order_position
        self.long_position.order_state = order.order_state
        self.long_position.executed_price_avg = order.executed_price_avg
        if order.order_state == RECEIPT and order.order_position == PURCHASE:
            self.long_position.order_amount += order.order_amount
            self.long_position.open_amount += order.open_amount
        elif order.executed_amount:
            self.long_position.open_amount -= executed_amount
            self.long_position.executed_amount_sum += executed_amount
            self.short_position.profit += order.current_profit
            self.short_position.net_profit += order.current_net_profit
            self.total_profit += order.current_profit
            self.total_fee += order.current_total_fee
            self.net_profit += order.current_net_profit
            self.long_position_history[self.long_position.executed_time] = self.long_position.executed_price_avg
            if not self.trading_halted:
                pass
                # self.sell(executed_amount)

    def update_short_position(self, order):
        executed_amount = abs(order.executed_amount)
        self.short_position.episode_number = 'SP'
        self.short_position.item_name = order.item_name
        self.short_position.order_price = order.order_price
        self.episodes[self.short_position.episode_number] = self.short_position
        self.short_position.executed_time = order.executed_time
        self.short_position.order_number = order.order_number
        self.short_position.order_position = order.order_position
        self.short_position.order_state = order.order_state
        self.short_position.executed_price_avg = order.executed_price_avg
        if order.order_state == RECEIPT and order.order_position == SELL:
            self.short_position.order_amount += order.order_amount
            self.short_position.open_amount += order.open_amount
        elif order.executed_amount:
            self.short_position.open_amount -= executed_amount
            self.short_position.executed_amount_sum += executed_amount
            self.long_position.profit += order.current_profit
            self.long_position.net_profit += order.current_net_profit
            self.total_profit += order.current_profit
            self.total_fee += order.current_total_fee
            self.net_profit += order.current_net_profit
            self.short_position_history[self.short_position.executed_time] = self.short_position.executed_price_avg
            if not self.trading_halted:
                pass
                # self.buy(executed_amount)

    def update_open_position(self, order):
        self.post_blue('(OPEN1)', self.open_position.episode_number, 'order', self.open_position.order_amount,
                       'executed', self.open_position.executed_amount_sum,
                       'open', self.open_position.open_amount,
                       'holding', self.futures.holding_amount,
                       'virtual', self.futures.virtual_holding_amount,
                       'order.executed', order.executed_amount)

        # if self.episode_count != self.open_position.get_episode_count():
        if not self.open_position.episode_count or self.open_position.completed:
            previous_episode_count = self.open_position.episode_count
            previous_open_amount = self.open_position.open_amount
            self.open_position.order_amount -= previous_open_amount
            self.open_position.open_amount = 0
            self.open_position = Episode()
            self.open_position.episode_count = previous_episode_count + 1
            self.open_position.set_episode_number('E')
            self.open_position.item_name = order.item_name
            self.open_position.order_amount = previous_open_amount
            self.open_position.open_amount = previous_open_amount
            self.episodes[self.open_position.episode_number] = self.open_position
        self.open_position.executed_time = order.executed_time
        self.open_position.order_number = order.order_number
        self.open_position.order_position = order.order_position
        self.open_position.order_state = order.order_state
        self.open_position.order_price = order.order_price

        if order.order_position in (PURCHASE, SELL) and order.order_state == RECEIPT:
            self.open_position.order_amount += order.order_amount
            self.open_position.open_amount += order.open_amount

        executed_amount = abs(order.executed_amount)
        if executed_amount:
            self.open_position.open_amount -= executed_amount
            self.open_position.executed_amount_sum += executed_amount
            self.open_position.purchase_sum += executed_amount * order.executed_price_avg
            executed_purchase_sum = self.open_position.purchase_sum
            amount_sum = self.open_position.executed_amount_sum
            self.open_position.executed_price_avg = round(executed_purchase_sum / amount_sum, 2)
            self.futures.virtual_holding_amount += order.executed_amount
            self.open_position_history[order.executed_time] = \
                (order.executed_price_avg, self.open_position.get_episode_number())
            if self.open_position.executed_amount_sum == self.episode_amount:
                self.open_position.completed = True
            self.close_position.virtual_open_amount += executed_amount
            self.counter_trade(order)

        self.post_blue('(OPEN2)', self.open_position.episode_number, 'order', self.open_position.order_amount,
                       'executed', self.open_position.executed_amount_sum,
                       'open', self.open_position.open_amount,
                       'holding', self.futures.holding_amount,
                       'virtual', self.futures.virtual_holding_amount)

    def update_close_position(self, order):
        self.post_blue('(CLOSE1)', self.close_position.episode_number, 'order', self.close_position.order_amount,
                       'executed', self.close_position.executed_amount_sum,
                       'open', self.close_position.open_amount,
                       'holding', self.futures.holding_amount,
                       'virtual', self.futures.virtual_holding_amount)

        if not self.close_position.episode_count or self.close_position.completed:
            previous_episode_count = self.close_position.episode_count
            self.close_position = Episode()
            self.close_position.episode_count = previous_episode_count + 1
            self.close_position.set_episode_number('S')
            self.close_position.item_name = order.item_name
            self.episodes[self.close_position.episode_number] = self.close_position
        self.close_position.executed_time = order.executed_time
        self.close_position.order_number = order.order_number
        self.close_position.order_position = order.order_position
        self.close_position.order_state = order.order_state
        self.close_position.order_price = order.order_price

        if order.order_position in (PURCHASE, SELL) and order.order_state == RECEIPT:
            self.close_position.order_amount += order.order_amount
            self.close_position.open_amount += order.open_amount
            self.close_position.virtual_open_amount += order.open_amount

        executed_amount = abs(order.executed_amount)
        if executed_amount:
            self.close_position.open_amount -= executed_amount
            self.close_position.executed_amount_sum += executed_amount
            self.close_position.executed_sum += executed_amount * order.executed_price_avg
            amount_sum = self.close_position.executed_amount_sum
            self.close_position.executed_price_avg = round(self.close_position.executed_sum / amount_sum, 2)
            self.close_position.profit += order.current_profit
            self.close_position.net_profit += order.current_net_profit
            self.futures.virtual_holding_amount += order.executed_amount
            self.close_position_history[order.executed_time] = \
                (order.executed_price_avg, self.close_position.get_episode_number())
            self.close_position.virtual_open_amount -= executed_amount
            self.close_position.executed_amount += executed_amount
            if not self.close_position.virtual_open_amount:
                self.close_position.completed = True
            self.post('holdings', self.futures.holding_amount, 'slope', self.futures.chart.PAR1_Slope[-1])
            if self.futures.holding_amount * self.futures.chart.PAR1_Slope[-1] >= 0:
                self.trade_by_trend(self.close_position.executed_amount)
                self.close_position.executed_amount = 0

            # if not self.close_position.open_amount:
            #     self.initiate_order(self.close_position.executed_amount_sum)

        self.post_blue('(CLOSE2)', self.close_position.episode_number, 'order', self.close_position.order_amount,
                       'executed', self.close_position.executed_amount_sum,
                       'open', self.close_position.open_amount,
                       'holding', self.futures.holding_amount,
                       'virtual', self.futures.virtual_holding_amount)

    def subsequent_orders(self, order):
        if order.open_amount < 0:
            self.post_magenta('(STOP) open amount is negative!!')
            # self.stop()

    def count_open_orders(self, order):
        if order.order_position == PURCHASE and order.order_state == RECEIPT:
            self.open_purchase_orders -= 1
            self.post('(COUNT)', 'open purchase orders', self.open_purchase_orders)
            if not self.open_purchase_orders:
                self.post('(COUNT)', 'purchase order UNLOCKED')
        elif order.order_position == SELL and order.order_state == RECEIPT:
            self.open_sale_orders -= 1
            self.post('(COUNT)', 'open sale orders', self.open_sale_orders)
            if not self.open_sale_orders:
                self.post('(COUNT)', 'sale order UNLOCKED')
        elif order.order_position == CORRECT_PURCHASE and order.order_state == CONFIRMED:
            self.open_purchase_correct_orders -= 1
            self.post('(COUNT)', 'open purchase correct orders', self.open_purchase_correct_orders)
            if not self.open_purchase_correct_orders:
                self.correct_purchases_ordered = False
                self.post('(COUNT)', 'purchase correct order UNLOCKED')
        elif order.order_position == CORRECT_SELL and order.order_state == CONFIRMED:
            self.open_sale_correct_orders -= 1
            self.post('(COUNT)', 'open sale correct orders', self.open_sale_correct_orders)
            if not self.open_sale_correct_orders:
                self.correct_sales_ordered = False
                self.post('(COUNT)', 'sale correct order UNLOCKED')
        elif order.order_position == CANCEL_PURCHASE and order.order_state == CONFIRMED:
            self.open_purchase_cancel_orders -= 1
            self.cancel_purchase_amount += order.order_amount
            self.long_position.order_amount -= order.order_amount
            self.long_position.open_amount -= order.order_amount
            if self.open_position.is_equivalent(PURCHASE):
                self.open_position.order_amount -= order.order_amount
                self.open_position.open_amount -= order.order_amount
            else:
                self.close_position.order_amount -= order.order_amount
                self.close_position.open_amount -= order.order_amount
            self.post('(COUNT)', 'open purchase cancel orders', self.open_purchase_cancel_orders)
            self.post('(COUNT)', 'cancel purchase amount', self.cancel_purchase_amount)
            if not self.open_purchase_cancel_orders:
                self.post('(COUNT)', 'purchase cancel order UNLOCKED')
                self.cancel_purchases_ordered = False
                self.buy(self.cancel_purchase_amount)
                self.cancel_purchase_amount = 0
        elif order.order_position == CANCEL_SELL and order.order_state == CONFIRMED:
            self.open_sale_cancel_orders -= 1
            self.cancel_sale_amount += order.order_amount
            self.short_position.order_amount -= order.order_amount
            self.short_position.open_amount -= order.order_amount
            if self.open_position.is_equivalent(SELL):
                self.open_position.order_amount -= order.order_amount
                self.open_position.open_amount -= order.order_amount
            else:
                self.close_position.order_amount -= order.order_amount
                self.close_position.open_amount -= order.order_amount
            self.post('(COUNT)', 'open sale cancel orders', self.open_sale_cancel_orders)
            self.post('(COUNT)', 'cancel sale amount', self.cancel_sale_amount)
            if not self.open_sale_cancel_orders:
                self.post('(COUNT)', 'sale cancel order UNLOCKED')
                self.cancel_sales_ordered = False
                self.sell(self.cancel_sale_amount)
                self.cancel_sale_amount = 0
        elif self.settle_up_in_progress:
            self.open_orders -= 1
            if not self.open_orders:
                self.settle_up_proper()
        elif self.finish_up_in_progress:
            self.open_orders -= 1
            if not self.open_orders:
                self.finish_up_proper()

    def count_clear_orders(self, order):
        self.post('(COUNT CLEAR)', 'order position', order.order_position)

    def post_order_details(self, order):
        msg = (order.item_name, order.order_position, order.order_state)
        msg += ('order:' + str(order.order_amount), 'executed_each:' + str(order.executed_amount))
        msg += ('open:' + str(order.open_amount), 'number:' + str(order.order_number))
        msg += ('executed:' + str(order.executed_price_avg), )
        msg += ('holding:' + str(self.futures.holding_amount),)
        executed_time = str(order.executed_time)
        time_format = executed_time[:2] + ':' + executed_time[2:4] + ':' + executed_time[4:]
        self.post_green('(EXECUTION)', *msg)
        self.post_blue('(DEBUG)', time_format, 'Purchases', len(self.futures.purchases),
                       'Sales', len(self.futures.sales))

        for sale in self.futures.sales.values():
            self.post_blue('sale    ', 'order', sale.order_amount, 'executed', sale.executed_amount_sum,
                           'open', sale.open_amount)
        for purchase in self.futures.purchases.values():
            self.post_blue('purchase', 'order', purchase.order_amount, 'executed', purchase.executed_amount_sum,
                           'open', purchase.open_amount)

    def report_success_order(self, order):
        if order.order_position == CANCEL_PURCHASE:
            self.post('(REPORT)', 'cancel purchases ordered successfully', self.open_purchase_cancel_orders)
        if order.order_position == CANCEL_SELL:
            self.post('(REPORT)', 'cancel sales ordered successfully', self.open_sale_cancel_orders)

    def report_fail_order(self, order):
        if self.cancel_purchases_ordered:
            self.open_purchase_cancel_orders -= 1
            self.post('(REPORT)', 'FAIL, open cancel purchase orders', self.open_purchase_cancel_orders)
            if not self.open_purchase_cancel_orders:
                self.cancel_purchases_ordered = False
                self.post('(REPORT)', 'cancel purchase order UNLOCKED')
        elif self.cancel_sales_ordered:
            self.open_sale_cancel_orders -= 1
            self.post('(REPORT)', 'FAIL, open sale orders', self.open_sale_cancel_orders)
            if not self.open_sale_cancel_orders:
                self.cancel_sales_ordered = False
                self.post('(REPORT)', 'cancel sale order UNLOCKED')
        elif self.correct_purchases_ordered:
            self.open_purchase_correct_orders -= 1
            self.post('(REPORT)', 'FAIL, open purchase correct orders', self.open_purchase_correct_orders)
            if not self.open_purchase_correct_orders:
                self.correct_purchases_ordered = False
                self.post('(REPORT)', 'correct purchase order UNLOCKED')
        elif self.correct_sales_ordered:
            self.open_sale_correct_orders -= 1
            self.post('(REPORT)', 'FAIL, open sale correct orders', self.open_sale_correct_orders)
            if not self.open_sale_correct_orders:
                self.correct_sales_ordered = False
                self.post('(REPORT)', 'correct sale order UNLOCKED')
        else:
            self.post('(REPORT)', 'Something is terribly wrong')
            self.stop()

    def customize_past_chart(self, item):
        chart = item.chart
        chart['MA5'] = chart.Close.rolling(5, 1).mean().apply(lambda x:round(x, 3))
        chart['MA10'] = chart.Close.rolling(10, 1).mean().apply(lambda x:round(x, 3))
        chart['MA20'] = chart.Close.rolling(20, 1).mean().apply(lambda x:round(x, 3))
        chart['Diff5'] = chart.MA5.diff().fillna(0).apply(lambda x:round(x, 3))
        chart['Diff10'] = chart.MA10.diff().fillna(0).apply(lambda x:round(x, 3))
        chart['Diff20'] = chart.MA20.diff().fillna(0).apply(lambda x:round(x, 3))
        chart['DiffDiff5'] = chart.Diff5.diff().fillna(0).apply(lambda x:round(x, 3))
        chart['DiffDiff10'] = chart.Diff10.diff().fillna(0).apply(lambda x:round(x, 3))
        chart['DiffDiff20'] = chart.Diff20.diff().fillna(0).apply(lambda x:round(x, 3))
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

        PAR1_Slope = numpy.polyfit(x1, PAR1, 1)[0]
        chart.loc[x1_interval, 'X1'] = x1
        chart.loc[x1_interval, 'PAR1_Slope'] = PAR1_Slope

        x_slope_interval = chart.index[-self.par1_slope_interval:]
        x_slopeslope = chart.loc[x_slope_interval, 'X1']
        y_slopeslope = chart.loc[x_slope_interval, 'PAR1_Slope']
        PAR1_SlopeSlope = numpy.polyfit(x_slopeslope, y_slopeslope, 1)[0]

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

    def update_custom_chart(self, item):
        chart = item.chart
        chart_len = len(chart)
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

        current_time = chart.index[-1]
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

        PAR1_Slope = numpy.polyfit(x1, PAR1, 1)[0]
        chart.loc[x1_interval, 'X1'] = x1
        chart.loc[x1_interval, 'PAR1'] = PAR1

        chart.loc[x1_interval, 'BL'] = PAR1 - self.interval
        chart.loc[x1_interval, 'SL'] = PAR1 + self.interval
        chart.loc[x1_interval, 'LLL'] = PAR1 - self.loss_cut
        chart.loc[x1_interval, 'ULL'] = PAR1 + self.loss_cut

        x_slope_interval = chart.index[-self.par1_slope_interval:]
        x_slopeslope = chart.loc[x_slope_interval, 'X1']
        y_slopeslope = chart.loc[x_slope_interval, 'PAR1_Slope']
        PAR1_SlopeSlope = numpy.polyfit(x_slopeslope, y_slopeslope, 1)[0]

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

    def display_chart(self):
        chart = self.futures.chart
        chart_len = len(chart)
        if not chart_len:
            return

        self.trader.chart_ax.clear()

        # Axis ticker formatting
        if chart_len // 30 > len(self.chart_locator) - 1:
            for index in range(len(self.chart_locator) * 30, chart_len, 30):
                time_format = chart.index[index].strftime('%H:%M')
                self.chart_locator.append(index)
                self.chart_formatter.append(time_format)
        self.trader.chart_ax.xaxis.set_major_locator(ticker.FixedLocator(self.chart_locator))
        self.trader.chart_ax.xaxis.set_major_formatter(ticker.FixedFormatter(self.chart_formatter))

        # Axis yticks & lines
        max_price = chart.High.max()
        min_price = chart.Low.min()
        if max_price > self.top_price or min_price < self.bottom_price:
            self.top_price = math.ceil(max_price / self.interval) * self.interval
            self.bottom_price = math.floor(min_price / self.interval) * self.interval
            self.interval_prices = numpy.arange(self.bottom_price, self.top_price + self.interval, self.interval)
            self.loss_cut_prices = numpy.arange(self.bottom_price + self.interval - self.loss_cut, self.top_price, self.interval)
        self.trader.chart_ax.grid(axis='x', alpha=0.5)
        self.trader.chart_ax.set_yticks(self.interval_prices)
        for price in self.interval_prices:
            self.trader.chart_ax.axhline(price, alpha=0.5, linewidth=0.2)
        for price in self.loss_cut_prices:
            self.trader.chart_ax.axhline(price, alpha=0.4, linewidth=0.2, color='Gray')

        # Current Price Annotation
        current_time = chart_len
        current_price = chart.Close.iloc[-1]
        self.trader.chart_ax.text(current_time + 0.5, current_price, format(current_price, ',.2f'))

        # Moving average
        x = range(0, len(chart))
        self.trader.chart_ax.plot(x, chart.MA5, label='MA5', color='Magenta')
        self.trader.chart_ax.plot(x, chart.MA10, label='MA10', color='RoyalBlue')
        self.trader.chart_ax.plot(x, chart.MA20, label='MA20', color='Gold')
        self.trader.chart_ax.legend(loc='best')

        # Slope
        x_range = range(chart_len - 1, chart_len + 1)
        self.slope = numpy.polyfit(x_range, chart.MA5[-2:], 1)
        x = range(chart_len - 20, chart_len)
        y = numpy.poly1d(self.slope)
        self.trader.chart_ax.plot(x, y(x), color='Sienna')

        # Regression
        x1_len = self.r1_interval
        x3_len = self.r3_interval
        if chart_len < x1_len:
            x1_len = chart_len
        if chart_len < x3_len:
            x3_len = chart_len

        self.trader.chart_ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:], color='DarkOrange')
        self.trader.chart_ax.plot(chart.X3[-x3_len:], chart.PAR3[-x3_len:], color='Cyan')
        self.trader.chart_ax.plot(chart.X3[-x3_len:], chart.MAR3[-x3_len:], color='DarkSlateGray')
        self.trader.chart_ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] + self.loss_cut, color='Gray')
        self.trader.chart_ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] - self.loss_cut, color='Gray')
        self.trader.chart_ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] - self.interval, color='DarkGray')
        self.trader.chart_ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] + self.interval, color='DarkGray')

        # Set lim
        x2 = chart_len
        x1 = x2 - self.chart_scope
        if x1 < 0:
            x1 = 0
        elif x1 > x2 - 1:
            x1 = x2 - 1
        y1 = self.get_min_price(x1, x2) - 0.1
        y2 = self.get_max_price(x1, x2) + 0.1
        self.trader.chart_ax.set_xlim(x1, x2)
        self.trader.chart_ax.set_ylim(y1, y2)

        # After price data acquired
        if self.start_time:
            self.annotate_chart(current_time, x1, x2, y1, y2)

        # Draw chart
        candlestick2_ohlc(self.trader.chart_ax, chart.Open, chart.High, chart.Low, chart.Close,
                          width=0.4, colorup='red', colordown='blue')
        self.trader.chart_fig.tight_layout()
        self.trader.chart_canvas.draw()

    def annotate_chart(self, current_time, x1, x2, y1, y2):
        # Start time
        if self.start_time > x1:
            self.trader.chart_ax.plot(self.start_time, self.start_price, marker='o', markersize=3, color='Lime')
            self.trader.chart_ax.vlines(self.start_time, y1, self.start_price, alpha=0.8, linewidth=0.2, color='Green')
            self.trader.chart_ax.text(self.start_time, y1 + 0.05, self.start_comment, color='RebeccaPurple')

        # Purchase / Sale orders
        chart = self.futures.chart
        total_range = y2 - y1
        offset = total_range * 0.030
        x = current_time
        y = chart.ULL[-1]
        sales = copy.deepcopy(self.futures.sales)
        for order in sales.values():
            if order.open_amount:
                y += offset
                self.trader.chart_ax.text(x, y, '({}/{})'.format(order.executed_amount_sum, order.order_amount))

        y = chart.LLL[-1] - offset
        purchases = copy.deepcopy(self.futures.purchases)
        for order in purchases.values():
            if order.open_amount:
                y -= offset
                self.trader.chart_ax.text(x, y, '({}/{})'.format(order.executed_amount_sum, order.order_amount))

        # Trade history
        try:
            for trade_time, price in self.long_position_history.items():
                x = self.to_min_count2(trade_time)
                if x > x1:
                    self.trader.chart_ax.text(x + 0.5, price, 'P')
                    self.trader.chart_ax.plot(x, price, marker='o', markersize=4, color='SkyBlue')
            for trade_time, price in self.short_position_history.items():
                x = self.to_min_count2(trade_time)
                if x > x1:
                    self.trader.chart_ax.text(x + 0.5, price, 'S')
                    self.trader.chart_ax.plot(x, price, marker='o', markersize=4, color='MidNightBlue')
            for trade_time, data in self.open_position_history.items():
                x = self.to_min_count2(trade_time)
                if x > x1:
                    self.trader.chart_ax.text(x + 0.5, data[0] + offset, 'E' + data[1])
            # for trade_time, data in self.close_position_history.items():
            #     x = self.to_min_count2(trade_time)
            #     if x > x1:
            #         self.trader.ax.text(x + 0.5, data[0] + offset, 'S' + data[1])
        except Exception as e:
            self.warning('Runtime warning(during trade history):', e)

    def get_regression(self, x, y, interval, predict_len, polynomial_features):
        if interval is None:
            interval = self.r3_interval

        x_len = len(x)
        if x_len < interval:
            interval = x_len

        x2 = x_len
        x1 = x2 - interval
        x3 = x2 + predict_len
        x_regression = numpy.arange(x1, x3)
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

    def get_buy_limit(self):
        buy_limit = float(self.futures.chart.PAR1[-1]) - self.interval
        corrected_buy_limit = wmath.get_nearest_bottom(buy_limit)
        return corrected_buy_limit

    def get_sell_limit(self):
        sell_limit = float(self.futures.chart.PAR1[-1]) + self.interval
        corrected_sell_limit = wmath.get_nearest_top(sell_limit)
        return corrected_sell_limit

    def get_max_price(self, x1, x2):
        max_price = self.futures.chart.High[x1:x2].max()
        return max_price

    def get_min_price(self, x1, x2):
        min_price = self.futures.chart.Low[x1:x2].min()
        return min_price