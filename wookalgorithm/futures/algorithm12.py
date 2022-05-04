from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QMutex, QMutexLocker
import numpy
from mplfinance.original_flavor import candlestick2_ohlc
from matplotlib import ticker
from matplotlib.animation import FuncAnimation
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from datetime import datetime
from wookitem import Order, Episode, AlgorithmItem, FuturesAlgorithmItem, Timeline, OrderStatus
from wookutil import wmath, Display
from wookdata import *
from wookalgorithm.futuresalgorithmbase import FuturesAlgorithmBase
import pandas
import math, copy, time

'''
Original Algorithm (2021, 12, 15)
1. Price average first degree regression model
2. Dynamic volatility (no shift, moving loss cut) 
3. Limit order
4. Multiple episode
5. Concentrate on continuous automatic trading
6. R1 interval modification by trend deviation
7. Trend scalping, Strangle scalping, Buy and hold strategy
8. Dynamic settlement (immediate counter trade after settlement)
9. Long / Short position system
10. Trade at PA
'''

class FMAlgorithm12(FuturesAlgorithmBase):
    def __init__(self, trader, log):
        super().__init__(trader, log)
        self.futures = None

        # Episode history
        self.long_episode_history = dict()
        self.short_episode_history = dict()

        # Timeline
        self.timeline = Timeline(self, log)
        self.timeline_max = -28
        self.timeline_len = self.timeline_max
        self.pause_timeline = False
        self.status_len = 1

        # Variables
        self.slope = None
        self.trading_halted = False
        self.default_r1_interval = 5
        self.margin_ratio = 0.1
        self.cancel_purchase_amount = 0
        self.cancel_sale_amount = 0
        self.cancel_margin = 0.00
        self.profit_rate_margin = -0.08
        self.trend_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        self.last_episode = None

        # Regression
        self.polynomial_features1 = PolynomialFeatures(degree=1, include_bias=False)
        self.polynomial_features2 = PolynomialFeatures(degree=2, include_bias=False)
        self.polynomial_features3 = PolynomialFeatures(degree=3, include_bias=False)
        self.linear_regression = LinearRegression()
        self.r1_interval = self.default_r1_interval
        self.r3_interval = 9
        self.par1_slope_interval = 4

    def start(self, broker, capital, interval, loss_cut, fee, minimum_transaction_amount):
        self.futures = FuturesAlgorithmItem('101S3000')
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

        # self.post_magenta('SLOPE', self.chart.PAR1_Slope[-1])
        # self.post_magenta('SLOPESLOPE', self.chart.PAR1_SlopeSlope[-1])

        if self.trading_halted:
            return

        if self.work_in_progress():
            return

        # self.futures.update_profit(item.current_price)
        # self.post_without_repetition('(DEBUG)', 'profit', self.futures.profit, 'profit rate', self.futures.profit_rate)

        self.monitor_trend_deviation(item.current_price)
        self.correct_order_prices(item.current_price)

    def start_work(self, current_price):
        now = datetime.now()
        self.start_time_text = now.strftime('%H:%M')
        self.start_time = self.to_min_count(self.start_time_text)
        self.start_price = current_price
        self.start_comment = 'start\n' + self.start_time_text + '\n' + format(self.start_price, ',')
        self.episode_amount = int((self.capital / self.margin_ratio) // (current_price * MULTIPLIER))
        self.strangle_episode_amount = ((self.episode_amount // 2) * 2) // 2
        self.initiate_order()

    def initiate_order(self, amount=0, price=0, order_type='LIMIT'):
        self.trade()

    def trade(self):
        if self.long_episode.virtual_open_amount < 0:
            self.long_episode.virtual_open_amount = 0
            self.post_magenta('@ == long episode virtual open amount is negative maybe no further order executed ==')
        if self.short_episode.virtual_open_amount < 0:
            self.short_episode.virtual_open_amount = 0
            self.post_magenta('@ == short episode virtual open amount is negative maybe no further order executed ==')

        episode_amount = 0
        purchase_target_amount = 0
        sale_target_amount = 0

        if self.strategy == TREND_SCALPING_STRATEGY:
            episode_amount = self.episode_amount
            purchase_target_amount = self.episode_amount if self.futures.chart.PAR1_Slope[-1] >= 0 else 0
            sale_target_amount = self.episode_amount if self.futures.chart.PAR1_Slope[-1] < 0 else 0
        elif self.strategy == STRANGLE_SCALPING_STRATEGY:
            episode_amount = self.strangle_episode_amount * 2
            purchase_target_amount = self.strangle_episode_amount
            sale_target_amount = self.strangle_episode_amount
        elif self.strategy == BUY_AND_HOLD_STRATEGY:
            episode_amount = self.episode_amount
            purchase_target_amount = episode_amount if self.futures.chart.PAR1_Slope[-1] >= 0 else -episode_amount
            sale_target_amount = episode_amount if self.futures.chart.PAR1_Slope[-1] < 0 else -episode_amount

        self.set_transaction(episode_amount, purchase_target_amount, sale_target_amount)

    def set_transaction(self, episode_amount, purchase_target_amount, sale_target_amount):
        open_amount = self.long_episode.virtual_open_amount + self.short_episode.virtual_open_amount
        available_amount = episode_amount - open_amount

        purchase_open_amount = self.long_episode.virtual_open_amount
        purchase_amount = self.futures.holding_amount + purchase_open_amount
        purchase_order_amount = purchase_target_amount - purchase_amount
        purchase_surplus_amount = -1 * self.futures.holding_amount - purchase_open_amount - available_amount
        purchase_surplus_amount = purchase_surplus_amount if purchase_surplus_amount > 0 else 0
        purchase_available_amount = available_amount + purchase_surplus_amount
        purchase_order_amount = min(purchase_order_amount, purchase_available_amount)

        sale_open_amount = self.short_episode.virtual_open_amount
        sale_amount = sale_open_amount - self.futures.holding_amount
        sale_order_amount = sale_target_amount - sale_amount
        sale_surplus_amount = self.futures.holding_amount - sale_open_amount - available_amount
        sale_surplus_amount = sale_surplus_amount if sale_surplus_amount > 0 else 0
        # sale_available_amount = self.episode_amount - open_amount + sale_surplus_amount
        sale_available_amount = available_amount + sale_surplus_amount
        sale_order_amount = min(sale_order_amount, sale_available_amount)

        self.debug('======= Trade by Strangle ========')
        self.debug('open_amount', open_amount)
        self.debug('available amount', available_amount)
        self.debug('=========== Purchase =============')
        self.debug('purchase target   ', purchase_target_amount)
        self.debug('purchase open     ', purchase_open_amount)
        self.debug('purchase          ', purchase_amount)
        self.debug('purchase surplus  ', purchase_surplus_amount)
        self.debug('purchase available', purchase_available_amount)
        self.debug('purchase order    ', purchase_order_amount)
        self.debug('============= Sale ===============')
        self.debug('sale target   ', sale_target_amount)
        self.debug('sale open     ', sale_open_amount)
        self.debug('sale          ', sale_amount)
        self.debug('sale surplus  ', sale_surplus_amount)
        self.debug('sale available', sale_available_amount)
        self.debug('sale order    ', sale_order_amount)

        if purchase_order_amount > 0:
            self.buy(purchase_order_amount)
        if sale_order_amount > 0:
            self.sell(sale_order_amount)

    def go_trend_scalping(self):
        self.strategy = TREND_SCALPING_STRATEGY

    def go_strangle_scalping(self):
        self.strategy = STRANGLE_SCALPING_STRATEGY

    def set_r1_interval(self):
        now = datetime.now().replace(second=0, microsecond=0)
        interval = now - self.trend_start
        if interval.seconds < (self.default_r1_interval - 1) * 60:
            self.r1_interval = interval.seconds // 60 + 2
            self.post_magenta('R1 interval', self.r1_interval)

    def monitor_trend_deviation(self, current_price):
        if self.strategy != BUY_AND_HOLD_STRATEGY:
            return

        order_price = self.get_price_average()
        if self.futures.holding_amount > 0:
            if self.chart.PAR1_Slope[-1] < 0:
                order_amount = self.futures.holding_amount - self.short_episode.virtual_open_amount
                if order_amount > 0:
                    # self.sell(order_amount, 0, 'MARKET')
                    self.sell(order_amount, order_price, 'LIMIT')
        elif self.futures.holding_amount < 0:
            if self.chart.PAR1_Slope[-1] > 0:
                order_amount = -self.futures.holding_amount - self.long_episode.virtual_open_amount
                if order_amount > 0:
                    # self.buy(order_amount, 0, 'MARKET')
                    self.buy(order_amount, order_price, 'LIMIT')

        # if self.futures.holding_amount > 0:
        #     if self.chart.PAR1_Slope[-1] < 0:
        #         order_amount = self.futures.holding_amount - self.short_episode.virtual_open_amount
        #         if order_amount > 0:
        #             self.sell(order_amount, 0, 'MARKET')
        # elif self.futures.holding_amount < 0:
        #     if self.chart.PAR1_Slope[-1] > 0:
        #         order_amount = -self.futures.holding_amount - self.long_episode.virtual_open_amount
        #         if order_amount > 0:
        #             self.buy(order_amount, 0, 'MARKET')

        # if self.futures.profit_rate < self.profit_rate_margin:
        #     self.post_magenta('(MONITOR)', 'Too Much Loss!!')
        #     # self.trend_start = datetime.now().replace(second=0, microsecond=0)
        #     # self.halt_trading()
        # elif current_price > self.futures.chart.ULL[-1]:
        #     self.post_magenta('(MONITOR)', 'Above Upper Loss Limit!!')
        #     # self.trend_start = datetime.now().replace(second=0, microsecond=0)
        #     # self.halt_trading()
        # elif current_price < self.futures.chart.LLL[-1]:
        #     self.post_magenta('(MONITOR)', 'Below Lower Loss Limint!!')
        #     # self.trend_start = datetime.now().replace(second=0, microsecond=0)
        #     # self.halt_trading()

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

    def buy(self, amount=0, given_price=0, order_type='LIMIT'):
        self.open_purchase_orders += 1
        self.post('(ORDER)', 'purchase order LOCKED', self.open_purchase_orders)
        if self.futures.holding_amount >= 0:
            price = self.get_price_average()
        else:
            price = self.get_buy_limit()
        price = given_price if given_price else price
        # price = price if price else self.get_buy_limit()
        amount = amount if amount else self.episode_amount
        self.long_episode.virtual_open_amount += amount
        self.futures.buy(price, amount, order_type)

    def sell(self, amount=0, given_price=0, order_type='LIMIT'):
        self.open_sale_orders += 1
        self.post('(ORDER)', 'sale order LOCKED', self.open_sale_orders)
        if self.futures.holding_amount <= 0:
            price = self.get_price_average()
        else:
            price = self.get_sell_limit()
        price = given_price if given_price else price
        # price = price if price else self.get_sell_limit()
        amount = amount if amount else self.episode_amount
        self.short_episode.virtual_open_amount += amount
        self.futures.sell(price, amount, order_type)

    def clear_up_holdings(self):
        self.post('CLEAR UP HOLDINGS!!!!!!')
        if self.futures.holding_amount > 0:
            self.futures.sell_off()
        elif self.futures.holding_amount < 0:
            self.futures.buy_off()

    def correct_order_prices(self, current_price):
        if self.futures.purchases and self.futures.holding_amount <= 0:
            order_price = self.get_price_average()
            if self.futures.holding_amount < 0:
                order_price = self.get_buy_limit()
            if self.long_position.order_price != order_price:
                if abs(current_price - order_price) > self.cancel_margin:
                    self.open_purchase_correct_orders = len(self.futures.purchases)
                    self.correct_purchases_ordered = True
                    self.post('(CORRECT)', 'correct purchase orders!!', self.open_purchase_correct_orders)
                    self.futures.correct_purchases(order_price)
        elif self.futures.sales and self.futures.holding_amount >= 0:
            order_price = self.get_price_average()
            if self.futures.holding_amount > 0:
                order_price = self.get_sell_limit()
            if self.short_position.order_price != order_price:
                if abs(current_price - order_price) > self.cancel_margin:
                    self.open_sale_correct_orders = len(self.futures.sales)
                    self.correct_sales_ordered = True
                    self.post('(CORRECT)', 'correct sale orders!!', self.open_sale_correct_orders)
                    self.futures.correct_sales(order_price)

    def correct_order_prices_deprecated(self, current_price):
        if self.futures.purchases and not (self.futures.holding_amount > 0):
            buy_limit = self.get_buy_limit()
            if self.long_position.order_price != buy_limit:
                if abs(current_price - buy_limit) > self.cancel_margin:
                    self.open_purchase_correct_orders = len(self.futures.purchases)
                    self.correct_purchases_ordered = True
                    self.post('(CORRECT)', 'correct purchase orders!!', self.open_purchase_correct_orders)
                    self.futures.correct_purchases(buy_limit)
        elif self.futures.sales and not (self.futures.holding_amount < 0):
            sell_limit = self.get_sell_limit()
            if self.short_position.order_price != sell_limit:
                if abs(current_price - sell_limit) > self.cancel_margin:
                    self.open_sale_correct_orders = len(self.futures.sales)
                    self.correct_sales_ordered = True
                    self.post('(CORRECT)', 'correct sale orders!!', self.open_sale_correct_orders)
                    self.futures.correct_sales(sell_limit)

    def update_execution_info(self, order):
        # self.post_cyan('(EXECUTION1)', 'holding', self.futures.holding_amount,
        #                'virtual', self.futures.virtual_holding_amount,
        #                'order.executed_amount', order.executed_amount)

        # Rejection
        # if order.order_state == ORDER_REJECTED:
        #     return

        # Update Algorithm item orders
        self.futures.update_orders(order)

        # Update algorithm item contracts
        if order.executed_amount:
            if self.futures.holding_amount * order.executed_amount >= 0:
                self.futures.add_contract(order)
            else:
                self.futures.settle_contracts(order)

        # Update episodes
        if order.order_position in PURCHASE_EQUIVALENT:
            self.update_long_position(order)
            self.update_long_episode(order)
        elif order.order_position in SELL_EQUIVALENT:
            self.update_short_position(order)
            self.update_short_episode(order)

        # Update timeline
        self.timeline.update(order)

        self.post_order_status()
        # self.post_cyan('(EXECUTION2)', 'holding', self.futures.holding_amount,
        #                'virtual', self.futures.virtual_holding_amount)

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
        self.display.register_chart()
        self.display.start()

    def update_long_position(self, order):
        executed_amount = abs(order.executed_amount)
        self.long_position.episode_number = 'LP'
        self.long_position.item_name = order.item_name
        self.positions[self.long_position.episode_number] = self.long_position
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
            # open_amount_change = executed_amount if order.open_amount >= 0 else 0
            # self.long_position.open_amount -= open_amount_change
            self.long_position.open_amount -= executed_amount
            self.long_position.executed_amount_sum += executed_amount
            self.long_position.profit += order.current_profit
            self.long_position.net_profit += order.current_net_profit
            self.total_profit += order.current_profit
            self.total_fee += order.current_total_fee
            self.net_profit += order.current_net_profit

    def update_short_position(self, order):
        executed_amount = abs(order.executed_amount)
        self.short_position.episode_number = 'SP'
        self.short_position.item_name = order.item_name
        self.short_position.order_price = order.order_price
        self.positions[self.short_position.episode_number] = self.short_position
        self.short_position.executed_time = order.executed_time
        self.short_position.order_number = order.order_number
        self.short_position.order_position = order.order_position
        self.short_position.order_state = order.order_state
        self.short_position.executed_price_avg = order.executed_price_avg
        if order.order_state == RECEIPT and order.order_position == SELL:
            self.short_position.order_amount += order.order_amount
            self.short_position.open_amount += order.open_amount
        elif order.executed_amount:
            # open_amount_change = executed_amount if order.open_amount >= 0 else 0
            # self.short_position.open_amount -= open_amount_change
            self.short_position.open_amount -= executed_amount
            self.short_position.executed_amount_sum += executed_amount
            self.short_position.profit += order.current_profit
            self.short_position.net_profit += order.current_net_profit
            self.total_profit += order.current_profit
            self.total_fee += order.current_total_fee
            self.net_profit += order.current_net_profit

    def update_long_episode(self, order):
        self.post_episode_info('LONG1', self.long_episode, order)

        # First episode
        if not self.long_episode.episode_count:
            self.long_episode = self.long_episode.next_episode('L')
            self.long_episode.item_name = order.item_name
            self.episodes[self.long_episode.episode_number] = self.long_episode

        # New episode creation after completion of settlement
        if not self.futures.virtual_holding_amount and order.executed_amount and self.long_episode.executed_amount_sum:
            self.long_episode = self.long_episode.next_episode('L')
            self.episodes[self.long_episode.episode_number] = self.long_episode

        if order.order_state == RECEIPT and order.order_position == PURCHASE:
            self.long_episode.order_amount += order.order_amount
            self.long_episode.open_amount += order.open_amount

        self.long_episode.executed_time = order.executed_time
        self.long_episode.order_number = order.order_number
        self.long_episode.original_order_number = order.original_order_number
        self.long_episode.order_position = order.order_position
        self.long_episode.order_state = order.order_state
        self.long_episode.order_price = order.order_price

        executed_amount = abs(order.executed_amount)
        if executed_amount:
            self.long_episode.open_amount -= executed_amount
            self.long_episode.virtual_open_amount -= executed_amount
            self.long_episode.executed_amount_sum += executed_amount
            self.long_episode.purchase_sum += executed_amount * order.executed_price_avg

            # Premature episode completion correction
            corrected_purchase_sum = 0
            if self.futures.holding_amount > 0 and \
                    self.futures.holding_amount != self.long_episode.executed_amount_sum:
            # if self.last_episode == self.short_episode and self.futures.virtual_holding_amount > 0:
                previous_long_episode = self.episodes[self.long_episode.get_previous_episode_number()]
                discrepancy = previous_long_episode.executed_amount_sum - self.short_episode.executed_amount_sum
                self.long_episode.order_amount += discrepancy
                self.long_episode.executed_amount_sum += discrepancy
                previous_long_episode.order_amount -= discrepancy
                previous_long_episode.executed_amount_sum -= discrepancy
                corrected_purchase_sum = discrepancy * previous_long_episode.executed_price_avg

                if discrepancy > 0:
                    self.post_red('Premature episode completion', 'discrepancy', discrepancy)

            executed_purchase_sum = self.long_episode.purchase_sum + corrected_purchase_sum
            amount_sum = self.long_episode.executed_amount_sum
            self.long_episode.executed_price_avg = round(executed_purchase_sum / amount_sum, 2)
            self.long_episode.profit += order.current_profit
            self.long_episode.net_profit += order.current_net_profit

            # New episode creation after over completion of settlement
            settlement_criteria = self.futures.virtual_holding_amount * self.futures.holding_amount
            if settlement_criteria < 0:
                self.long_episode.order_amount -= self.futures.holding_amount
                self.long_episode.executed_amount_sum -= self.futures.holding_amount
                self.long_episode = self.long_episode.next_episode('L')
                self.episodes[self.long_episode.episode_number] = self.long_episode
                self.long_episode.order_amount += self.futures.holding_amount
                self.long_episode.executed_amount_sum += self.futures.holding_amount

            self.futures.virtual_holding_amount += order.executed_amount

            # Opposite episode completion
            if self.last_episode == self.short_episode:
                self.short_episode = self.short_episode.next_episode('S')
                self.short_episode.virtual_open_amount = self.short_episode.open_amount
                self.episodes[self.short_episode.episode_number] = self.short_episode
            self.last_episode = self.long_episode

            # New transaction
            self.trade()

            # History
            self.long_episode_history[order.executed_time] = \
                (order.executed_price_avg, self.long_episode.episode_number)

        self.post_episode_info('LONG2', self.long_episode, order)

    def update_short_episode(self, order):
        self.post_episode_info('SHORT1', self.short_episode, order)

        # First episode
        if not self.short_episode.episode_count:
            self.short_episode = self.short_episode.next_episode('S')
            self.short_episode.item_name = order.item_name
            self.episodes[self.short_episode.episode_number] = self.short_episode

        # New episode creation after completion of settlement
        if not self.futures.virtual_holding_amount and order.executed_amount and self.short_episode.executed_amount_sum:
            self.short_episode = self.short_episode.next_episode('S')
            self.episodes[self.short_episode.episode_number] = self.short_episode

        if order.order_state == RECEIPT and order.order_position == SELL:
            self.short_episode.order_amount += order.order_amount
            self.short_episode.open_amount += order.open_amount

        self.short_episode.executed_time = order.executed_time
        self.short_episode.order_number = order.order_number
        self.short_episode.original_order_number = order.original_order_number
        self.short_episode.order_position = order.order_position
        self.short_episode.order_state = order.order_state
        self.short_episode.order_price = order.order_price

        executed_amount = abs(order.executed_amount)
        if executed_amount:
            self.short_episode.open_amount -= executed_amount
            self.short_episode.virtual_open_amount -= executed_amount
            self.short_episode.executed_amount_sum += executed_amount
            self.short_episode.purchase_sum += executed_amount * order.executed_price_avg

            # Premature episode completion correction
            corrected_purchase_sum = 0
            if self.futures.holding_amount < 0 and \
                    abs(self.futures.holding_amount) != self.short_episode.executed_amount_sum:
            # if self.last_episode == self.long_episode and self.futures.virtual_holding_amount < 0:
                previous_short_episode = self.episodes[self.short_episode.get_previous_episode_number()]
                discrepancy = previous_short_episode.executed_amount_sum - self.long_episode.executed_amount_sum
                self.short_episode.order_amount += discrepancy
                self.short_episode.executed_amount_sum += discrepancy
                previous_short_episode.order_amount -= discrepancy
                previous_short_episode.executed_amount_sum -= discrepancy
                corrected_purchase_sum = discrepancy * previous_short_episode.executed_price_avg

                if discrepancy > 0:
                    self.post_red('Premature completion', 'discrepancy', discrepancy)

            executed_purchase_sum = self.short_episode.purchase_sum + corrected_purchase_sum
            amount_sum = self.short_episode.executed_amount_sum
            self.short_episode.executed_price_avg = round(executed_purchase_sum / amount_sum, 2)
            self.short_episode.profit += order.current_profit
            self.short_episode.net_profit += order.current_net_profit

            # New episode creation after over completion of settlement
            settlement_criteria = self.futures.virtual_holding_amount * self.futures.holding_amount
            if settlement_criteria < 0:
                self.short_episode.order_amount -= abs(self.futures.holding_amount)
                self.short_episode.executed_amount_sum -= abs(self.futures.holding_amount)
                self.short_episode = self.short_episode.next_episode('S')
                self.episodes[self.short_episode.episode_number] = self.short_episode
                self.short_episode.order_amount += abs(self.futures.holding_amount)
                self.short_episode.executed_amount_sum += abs(self.futures.holding_amount)

            self.futures.virtual_holding_amount += order.executed_amount

            # Counter episode completion
            if self.last_episode == self.long_episode:
                self.long_episode = self.long_episode.next_episode('L')
                self.long_episode.virtual_open_amount = self.long_episode.open_amount
                self.episodes[self.long_episode.episode_number] = self.long_episode
            self.last_episode = self.short_episode

            # New transaction
            self.trade()

            # History
            self.short_episode_history[order.executed_time] = \
                (order.executed_price_avg, self.short_episode.episode_number)

        self.post_episode_info('SHORT2', self.short_episode, order)

    def subsequent_orders(self, order):
        if order.open_amount < 0:
            self.post_magenta('@(STOP) open amount is negative!!')
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
            if self.open_purchase_correct_orders <= 0:
                self.correct_purchases_ordered = False
                self.open_purchase_correct_orders = 0
                self.post('(COUNT)', 'purchase correct order UNLOCKED')
        elif order.order_position == CORRECT_SELL and order.order_state == CONFIRMED:
            self.open_sale_correct_orders -= 1
            self.post('(COUNT)', 'open sale correct orders', self.open_sale_correct_orders)
            if self.open_sale_correct_orders <= 0:
                self.correct_sales_ordered = False
                self.open_sale_correct_orders = 0
                self.post('(COUNT)', 'sale correct order UNLOCKED')
        elif order.order_position == CORRECT_PURCHASE and order.order_state == ORDER_REJECTED:
            self.open_purchase_correct_orders -= 1
            self.post('(COUNT)', 'open purchase correct orders', self.open_purchase_correct_orders)
            if self.open_purchase_correct_orders <= 0:
                self.correct_purchases_ordered = False
                self.open_purchase_correct_orders = 0
                self.post('(COUNT)', 'purchase correct order UNLOCKED')
        elif order.order_position == CORRECT_SELL and order.order_state == ORDER_REJECTED:
            self.open_sale_correct_orders -= 1
            self.post('(COUNT)', 'open sale correct orders', self.open_sale_correct_orders)
            if self.open_sale_correct_orders <= 0:
                self.correct_sales_ordered = False
                self.open_sale_correct_orders = 0
                self.post('(COUNT)', 'sale correct order UNLOCKED')
        elif order.order_position == CANCEL_PURCHASE and order.order_state == CONFIRMED:
            self.open_purchase_cancel_orders -= 1
            self.cancel_purchase_amount += order.order_amount
            self.long_position.order_amount -= order.order_amount
            self.long_position.open_amount -= order.order_amount
            self.post('(COUNT)', 'open purchase cancel orders', self.open_purchase_cancel_orders)
            self.post('(COUNT)', 'cancel purchase amount', self.cancel_purchase_amount)
            if not self.open_purchase_cancel_orders:
                self.post('(COUNT)', 'purchase cancel order UNLOCKED')
                self.cancel_purchases_ordered = False
                self.cancel_purchase_amount = 0
        elif order.order_position == CANCEL_SELL and order.order_state == CONFIRMED:
            self.open_sale_cancel_orders -= 1
            self.cancel_sale_amount += order.order_amount
            self.short_position.order_amount -= order.order_amount
            self.short_position.open_amount -= order.order_amount
            if not self.open_sale_cancel_orders:
                self.post('(COUNT)', 'sale cancel order UNLOCKED')
                self.cancel_sales_ordered = False
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

    def post_order_status(self):
        self.post_green('============================================')
        sales = list(self.timeline.order_status[-1].sales)
        for order_number in sales:
            status = self.timeline.order_status[-1].sales[order_number]
            self.post_green('sales    ({}/{}) {}'.format(status.executed_amount_sum, status.order_amount, order_number))
            # if order_number not in self.futures.sales:
            #     self.post_magenta('@ Gees sale not matched', status.order_number)
        purchases = list(self.timeline.order_status[-1].purchases)
        for order_number in purchases:
            status = self.timeline.order_status[-1].purchases[order_number]
            self.post_green('purchase ({}/{}) {}'.format(status.executed_amount_sum, status.order_amount, order_number))
            # if order_number not in self.futures.purchases:
            #     self.post_magenta('@ Gees purchase orders not matched', status.order_number)
        self.post_green('============================================')

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

        self.post_blue('=============================================')
        for sale in self.futures.sales.values():
            self.post_blue('sale    ', 'order', sale.order_amount, 'executed', sale.executed_amount_sum,
                           'open', sale.open_amount, 'number', sale.order_number)
        for purchase in self.futures.purchases.values():
            self.post_blue('purchase', 'order', purchase.order_amount, 'executed', purchase.executed_amount_sum,
                           'open', purchase.open_amount, 'number', purchase.order_number)
        self.post_blue('==============================================')

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
            self.post_magenta('@(REPORT)', 'Something is terribly wrong')
            # self.stop()

    def customize_past_chart(self, item):
        self.chart = self.futures.chart
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
        self.display.lock()
        before = time.time()

        chart = self.futures.chart
        chart_len = len(chart)
        if not chart_len:
            return

        ax = self.trader.chart_ax
        ax.clear()

        # Set lim
        x2 = chart_len
        x1 = x2 - self.chart_scope
        x1 = 0 if x1 < 0 else x1
        min_price = self.get_min_price(x1, x2)
        max_price = self.get_max_price(x1, x2)
        y1 = min_price - 0.1
        y2 = max_price + 0.1
        ax.set_xlim(x1, x2)
        ax.set_ylim(y1, y2)

        # Axis ticker formatting
        if chart_len // 30 > len(self.chart_locator) - 1:
            for index in range(len(self.chart_locator) * 30, chart_len, 30):
                time_format = chart.index[index].strftime('%H:%M')
                self.chart_locator.append(index)
                self.chart_formatter.append(time_format)
        ax.xaxis.set_major_locator(ticker.FixedLocator(self.chart_locator))
        ax.xaxis.set_major_formatter(ticker.FixedFormatter(self.chart_formatter))

        # Axis yticks & lines
        y_range = max_price - min_price
        hline_interval = wmath.get_nearest_top(y_range / 20)
        hline_interval = 0.05 if hline_interval < 0.05 else hline_interval
        hline_prices = numpy.arange(min_price, max_price, hline_interval)
        ax.grid(axis='x', alpha=0.5)
        ax.set_yticks(hline_prices)
        for price in hline_prices:
            ax.axhline(price, alpha=0.5, linewidth=0.2)

        # Current Price Annotation
        current_time = chart_len
        current_price = chart.Close.iloc[-1]
        # ax.text(current_time + 0.5, current_price, format(current_price, ',.2f'))
        ax.text(current_time, current_price, format(current_price, ',.2f'))

        # Moving average
        x = range(x1, x2)
        ax.plot(x, chart.MA5[x1:x2], label='MA5', color='Magenta')
        ax.plot(x, chart.MA10[x1:x2], label='MA10', color='RoyalBlue')
        ax.plot(x, chart.MA20[x1:x2], label='MA20', color='Gold')
        ax.legend(loc='best')

        # Slope
        # x_range = range(chart_len - 1, chart_len + 1)
        # self.slope = numpy.polyfit(x_range, chart.MA5[-2:], 1)
        # slope_x = range(chart_len - 20, chart_len)
        # y = numpy.poly1d(self.slope)
        # ax.plot(slope_x, y(slope_x), color='Sienna')

        # Regression
        x1_len = self.r1_interval
        x3_len = self.r3_interval
        if chart_len < x1_len:
            x1_len = chart_len
        if chart_len < x3_len:
            x3_len = chart_len

        ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:], color='DarkOrange')
        # ax.plot(chart.X3[-x3_len:], chart.PAR3[-x3_len:], color='Cyan')
        # ax.plot(chart.X3[-x3_len:], chart.MAR3[-x3_len:], color='DarkSlateGray')
        ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] + self.loss_cut, color='Gray')
        ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] - self.loss_cut, color='Gray')
        ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] - self.interval, color='DarkGray')
        ax.plot(chart.X1[-x1_len:], chart.PAR1[-x1_len:] + self.interval, color='DarkGray')

        # After price data acquired
        if self.start_time:
            self.annotate_chart(current_time, x1, x2, y1, y2)

        # Draw chart
        candlestick2_ohlc(ax, chart.Open, chart.High, chart.Low, chart.Close,
                          width=0.4, colorup='red', colordown='blue')
        # self.trader.chart_fig.tight_layout()

        after = time.time()
        elapsed_time = after - before
        # self.debug('Chart', elapsed_time)

        draw_before = time.time()
        # self.trader.chart_canvas.draw_idle()
        self.trader.chart_canvas.draw()
        draw_after = time.time()
        draw_elapsed_time = draw_after - draw_before
        # self.debug('Chart Draw', draw_elapsed_time)
        self.display.unlock()

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
            long_episode_history = copy.deepcopy(self.long_episode_history)
            for trade_time, data in long_episode_history.items():
                x = self.to_min_count2(trade_time)
                if x > x1:
                    self.trader.chart_ax.text(x + 0.5, data[0], data[1])
                    self.trader.chart_ax.plot(x, data[0], marker='o', markersize=4, color='GreenYellow')
            short_episode_history = copy.deepcopy(self.short_episode_history)
            for trade_time, data in short_episode_history.items():
                x = self.to_min_count2(trade_time)
                if x > x1:
                    self.trader.chart_ax.text(x + 0.5, data[0], data[1])
                    self.trader.chart_ax.plot(x, data[0], marker='o', markersize=4, color='SkyBlue')
        except Exception as e:
            self.warning('Runtime warning(during trade history):', e)

    def display_timeline(self):
        self.display.lock()
        before = time.time()

        if not self.timeline.changed:
            return
        self.timeline.changed = False

        ax = self.trader.timeline_ax
        ax.clear()

        for index, status in enumerate(self.timeline.order_status[self.timeline_len:]):
            x = (2 * index + 1) * 20

            # Holding amount
            if status.holding_amount > 0:
                ax.text(x + 15, -2, status.holding_amount, color='red')
            elif status.holding_amount < 0:
                ax.text(x + 11, -2, status.holding_amount, color='blue')
            else:
                ax.text(x + 15, -2, status.holding_amount)

            # Order status
            purchases = copy.deepcopy(status.purchases)
            for y, order in enumerate(purchases.values()):
                ax.text(x + 8, -20 - y * 10, '{}/{}'.format(order.executed_amount_sum, order.order_amount))
            sales = copy.deepcopy(status.sales)
            for y, order in enumerate(sales.values()):
                ax.text(x + 8, 15 + y * 10, '{}/{}'.format(order.executed_amount_sum, order.order_amount))

            # Arrows
            if status.execution == PURCHASE:
                ax.arrow(x, 0, 20, -10, color='green')
                ax.arrow(x + 20, -10, 20, 10, color='green')
            else:
                ax.arrow(x, 0, 20, 10, color='green')
                ax.arrow(x + 20, 10, 20, -10, color='green')

            # Episode
            if status.purchase_episode_changed:
                ax.vlines(x, -100, 0)
                ax.text(x + 2, -95, status.purchase_episode_number, color='purple')
            if status.sale_episode_changed:
                ax.vlines(x, 0, 100)
                ax.text(x + 2, 90, status.sale_episode_number, color='purple')

        timeline_len = len(self.timeline.order_status)
        xlim = timeline_len * 40
        if xlim > 1150 and self.pause_timeline:
            self.timeline.xlim = xlim + 40
            self.trader.timeline_canvas.resize(self.timeline.xlim, 360)
        if self.timeline_len:
            self.timeline.xlim = 1165

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(0, self.timeline.xlim)
        ax.set_ylim(-100, 100)
        ax.axhline(10)
        ax.axhline(0, linewidth=0.3)
        ax.axhline(-10)

        after = time.time()
        elapsed_time = after - before
        # self.debug('Timeline', elapsed_time)
        draw_before = time.time()
        # self.trader.timeline_canvas.draw_idle()
        self.trader.timeline_canvas.draw()
        # self.trader.timeline_canvas.blit()
        draw_after = time.time()
        draw_elapsed_time = draw_after - draw_before
        # self.debug('Timeline Draw', draw_elapsed_time)
        self.display.unlock()

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

    def get_price_average(self):
        price_average = float(self.futures.chart.PAR1[-1])
        if self.futures.chart.PAR1_Slope[-1] >= 0:
            corrected_price_average = wmath.get_nearest_top(price_average)
        else:
            corrected_price_average = wmath.get_nearest_bottom(price_average)
        return corrected_price_average

    def get_buy_limit(self):
        buy_limit = float(self.futures.chart.PAR1[-1]) - self.interval
        corrected_buy_limit = wmath.get_nearest_bottom(buy_limit)
        return corrected_buy_limit

    def get_sell_limit(self):
        sell_limit = float(self.futures.chart.PAR1[-1]) + self.interval
        corrected_sell_limit = wmath.get_nearest_top(sell_limit)
        return corrected_sell_limit

    def get_buy_limit_deprecated(self):
        buy_limit = float(self.futures.chart.PAR1[-1]) - self.interval
        corrected_buy_limit = wmath.get_nearest_bottom(buy_limit)
        return corrected_buy_limit

    def get_sell_limit_deprecated(self):
        sell_limit = float(self.futures.chart.PAR1[-1]) + self.interval
        corrected_sell_limit = wmath.get_nearest_top(sell_limit)
        return corrected_sell_limit

    def get_max_price(self, x1, x2):
        max_price = self.futures.chart.High[x1:x2].max()
        return max_price

    def get_min_price(self, x1, x2):
        min_price = self.futures.chart.Low[x1:x2].min()
        return min_price