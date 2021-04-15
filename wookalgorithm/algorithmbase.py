import copy
import pandas
from datetime import datetime
from PyQt5.QtCore import QEventLoop
from wookutil import WookUtil, WookLog, wmath
from wookitem import Item, BalanceItem, Order, AlgorithmItem
from wookchart import WookChart
from wookdata import *

class AlgorithmBase(WookUtil, WookLog):
    def __init__(self, log):
        WookLog.custom_init(self, log)
        self.log = log

        self.signal = None
        self.broker = None
        self.chart_prices = list()
        self.chart = None
        self.legitimate_chart = False
        self.is_running = False
        self.purchase_episode_shifted = False
        self.sale_episode_shifted = False
        self.sell_off_ordered = False
        # self.purchase_ordered = False
        # self.sale_ordered = False
        self.settle_up_in_progress = False
        self.finish_in_progress = False
        self.open_orders = 0
        self.open_correct_orders = 0
        self.open_cancel_orders = 0
        self.previous_situation = ''
        self.previous_msg = ()

        self.items = dict()
        self.orders = dict()
        self.episode_purchase = Order()
        self.episode_sale = Order()
        self.episode_purchase_number = ''
        self.episode_sale_number = ''
        self.episode_count = 0
        self.episode_amount = 0

        self.capital = 0
        self.interval = 0
        self.loss_cut = 0
        self.shift_interval = 0
        self.reference_price = 0
        self.buy_limit = 0
        self.loss_limit = 0
        self.minimum_transaction_amount = 0
        self.start_time_text = ''
        self.start_time = 0
        self.start_price = 0
        self.total_profit = 0
        self.total_fee = 0
        self.net_profit = 0
        self.fee = 0

    def init_chart(self):
        columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        self.chart = pandas.DataFrame(self.chart_prices, columns=columns)

    def set_parameters(self, broker, capital, interval, loss_cut, fee, minimum_transaction_amount):
        for item in self.items.values():
            item.set_broker(broker)
            item.set_log(self.log)
            item.fee_ratio = fee

        self.broker = broker
        self.capital = capital
        self.interval = interval
        self.loss_cut = loss_cut
        self.shift_interval = interval
        self.fee = fee
        self.minimum_transaction_amount = minimum_transaction_amount

    def stop(self):
        if not self.is_running:
            return
        self.post('STOPPED')

        # Open Orders cancellation
        self.clear_open_orders()

        # Init Fields
        self.broker = None
        self.chart_prices = list()
        self.chart = None
        self.legitimate_chart = False
        self.is_running = False
        self.purchase_episode_shifted = False
        self.sale_episode_shifted = False
        self.sell_off_ordered = False
        # self.purchase_ordered = False
        # self.sale_ordered = False
        self.settle_up_in_progress = False
        self.finish_in_progress = False
        self.open_orders = 0
        self.open_correct_orders = 0
        self.open_cancel_orders = 0
        self.previous_situation = ''
        self.previous_msg = ()

        self.orders.clear()
        self.episode_purchase = Order()
        self.episode_sale = Order()
        self.episode_purchase_number = ''
        self.episode_sale_number = ''
        self.episode_count = 0
        self.episode_amount = 0

        self.capital = 0
        self.interval = 0
        self.loss_cut = 0
        self.shift_interval = 0
        self.reference_price = 0
        self.buy_limit = 0
        self.loss_limit = 0
        self.minimum_transaction_amount = 0
        self.start_time_text = ''
        self.start_time = 0
        self.start_price = 0
        self.total_profit = 0
        self.total_fee = 0
        self.net_profit = 0
        self.fee = 0

    def resume(self):
        self.is_running = True

    def halt(self):
        self.is_running = False

    def set_reference(self, price):
        self.reference_price = price
        self.buy_limit = self.reference_price - self.interval
        self.loss_limit = self.buy_limit - self.loss_cut
        self.episode_amount = self.capital // self.buy_limit
        self.episode_count += 1

    def shift_reference_up(self):
        self.set_reference(self.reference_price + self.shift_interval)

    def shift_reference_down(self):
        self.set_reference(self.reference_price - self.shift_interval)

    def clear_open_orders(self):
        self.open_orders = len(self.broker.open_orders)
        open_orders = list(self.broker.open_orders.values())
        for order in open_orders:
            self.broker.cancel(order)

    def settle_up(self):
        self.post('(SETTLE UP) STARTED')
        self.settle_up_in_progress = True
        if len(self.broker.open_orders):
            self.clear_open_orders()
        else:
            self.settle_up_proper()

    def settle_up_proper(self):
        for item in self.items.values():
            if item.holding_amount:
                # self.broker.sell(item.item_code, 0, item.holding_amount, 'PRIMARY PEG')
                # self.broker.sell(item.item_code, item.ask_price, item.holding_amount, 'CONDITIONAL')
                self.broker.sell(item.item_code, item.ask_price, item.holding_amount, 'MARKET')

    def finish(self):
        self.finish_in_progress = True
        if len(self.broker.open_orders):
            self.clear_open_orders()
        else:
            self.finish_proper()

    def finish_proper(self):
        for item in self.items.values():
            if item.holding_amount:
                self.broker.sell(item.item_code, 0, item.holding_amount, 'MARKET')
        self.stop()

    def add_item(self, *items):
        for item in items:
            self.items[item.item_code] = item

    def normalize_number(self, number):
        number = str(number)
        if len(number) == 1:
            number = '0' + number
        return number

    def get_episode_purchase_number(self):
        normalized_count = self.normalize_number(self.episode_count)
        return normalized_count + 'P'

    def get_episode_sale_number(self):
        normalized_count = self.normalize_number(self.episode_count)
        return normalized_count + 'S'

    def get_next_purchase_number(self):
        if not self.episode_purchase_number:
            self.episode_purchase_number = '00P'
        next_count = int(self.episode_purchase_number[:-1]) + 1
        normalized_count = self.normalize_number(next_count)
        return normalized_count + 'P'

    def get_next_sale_number(self):
        if not self.episode_sale_number:
            self.episode_sale_number = '00S'
        next_count = int(self.episode_sale_number[:-1]) + 1
        normalized_count = self.normalize_number(next_count)
        return normalized_count + 'S'

    def display_situation(self, current_situation):
        if current_situation != self.previous_situation:
            self.post_without_repetition(current_situation)
            self.previous_situation = current_situation

    def post_without_repetition(self, *args):
        if args != self.previous_msg:
            self.debug('\033[93mALGORITHM', *args, '\033[97m')
            self.previous_msg = args

    def post(self, *args):
        self.debug('\033[93mALGORITHM', *args, '\033[97m')

    def copy_chart_prices(self):
        previous_chart_prices = copy.deepcopy(self.broker.chart_prices)
        self.chart_prices = previous_chart_prices + self.chart_prices

    def update_chart_prices(self, price, volume):
        current_time = datetime.now()
        current_time_str = current_time.strftime('%Y%m%d%H%M00')
        if not self.legitimate_chart:
            if self.chart_prices:
                previous_time = datetime.strptime(self.chart_prices[-1][TIME_], '%Y%m%d%H%M00')
                if previous_time <= current_time:
                    self.legitimate_chart = True
                else:
                    return

        if not self.chart_prices:
            price_data = [current_time_str, price, price, price, price, volume]
            self.chart_prices.append(price_data)
        elif current_time_str != self.chart_prices[-1][TIME_]:
            price_data = [current_time_str, price, price, price, price, volume]
            self.chart_prices.append(price_data)
        else:
            if price > self.chart_prices[-1][HIGH]:
                self.chart_prices[-1][HIGH] = price
            elif price < self.chart_prices[-1][LOW]:
                self.chart_prices[-1][LOW] = price
            self.chart_prices[-1][CLOSE] = price
            self.chart_prices[-1][VOLUME_] += volume

        self.chart = pandas.DataFrame(self.chart_prices, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])

    def get_moving_average_5(self):
        price_sum = 0
        data_length = len(self.chart_prices)
        if data_length < 5:
            chart_prices = self.chart_prices
        else:
            chart_prices = self.chart_prices[-5:]
            data_length = 5
        for prices in chart_prices:
            price_sum += prices[CLOSE]
        moving_average = round(price_sum / data_length)
        return moving_average