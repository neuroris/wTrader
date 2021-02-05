import copy
from datetime import datetime
from PyQt5.QtCore import QEventLoop
from wookutil import WookUtil, WookLog, wmath
from wookitem import Item, BalanceItem, Order, AlgorithmItem, OrderManager
from wookdata import *

class Algorithm(WookUtil, WookLog):
    def __init__(self, log):
        WookLog.custom_init(self, log)

        self.leverage = None
        self.balance_item = None
        self.broker = None
        self.orders = dict()
        self.log = log

        self.is_running = False
        self.capital = 0
        self.interval = 0
        self.loss_cut = 0
        self.start_time_text = ''
        self.start_time = 0
        self.start_price = 0
        self.reference_price = 0
        self.buy_limit = 0
        self.loss_limit = 0

        self.display = ''

    def start(self, broker, capital, interval, loss_cut):
        self.leverage = AlgorithmItem('122630')
        self.leverage.set_broker(broker)
        self.leverage.set_log(self.log)
        self.balance_item = BalanceItem()
        self.broker = broker
        self.capital = capital
        self.interval = interval
        self.loss_cut = loss_cut
        self.is_running = True

        # Charting & Monitoring
        broker.go_chart(self.leverage.item_code)
        broker.demand_monitoring_items_info(self.leverage)

        # Open Orders cancellation
        for order in broker.open_orders.values():
            self.broker.cancel(order)

    def stop(self):
        if not self.is_running:
            return

        # Open Orders cancellation
        for order in self.broker.open_orders.values():
            self.broker.cancel(order)

        # Init Fields
        self.broker = None
        self.orders.clear()
        self.leverage = None
        self.balance_item = None
        self.is_running = False
        self.capital = 0
        self.interval = 0
        self.loss_cut = 0
        self.start_time_text = ''
        self.start_time = 0
        self.start_price = 0
        self.reference_price = 0
        self.buy_limit = 0
        self.loss_limit = 0

    def resume(self):
        self.is_running = True

    def halt(self):
        self.is_running = False

    def set_reference(self, price):
        self.reference_price = price
        self.buy_limit = self.reference_price - self.interval
        self.loss_limit = self.buy_limit - self.loss_cut

    def shift_reference_up(self):
        self.set_reference(self.reference_price + self.interval)

    def shift_reference_down(self):
        self.set_reference(self.reference_price - self.interval)

    def update_transaction_info(self, item):
        # First time work
        if not self.start_price:
            self.start_time_text = datetime.now().strftime('%H:%M')
            self.start_time = self.to_min_count(self.start_time_text)
            self.start_price = item.current_price
            reference_price = wmath.get_bottom(item.current_price, self.interval)
            self.set_reference(reference_price)
            self.leverage.buy(self.buy_limit, self.capital // item.current_price)
            return

        # Trade
        if item.current_price >= self.reference_price + self.interval:
            current_display = 'situation 1'
            if current_display != self.display:
                self.debug('situation 1')
                self.display = current_display

            self.shift_reference_up()
            self.leverage.correct_purchase(self.buy_limit)
        elif item.current_price >= self.buy_limit + self.loss_cut:
            current_display = 'situation 2'
            if current_display != self.display:
                self.debug('situation 2')
                self.display = current_display

            self.leverage.sell_out(self.reference_price)
        elif item.current_price <= self.loss_limit:
            current_display = 'situation 4'
            if current_display != self.display:
                self.debug('situation 4')
                self.display = current_display

            self.leverage.sell_off()
            self.shift_reference_down()
            self.leverage.buy(self.buy_limit, self.capital // item.current_price)
        elif item.current_price <= self.reference_price - self.loss_cut:
            current_display = 'situation 3'
            if current_display != self.display:
                self.debug('situation 3')
                self.display = current_display

            self.leverage.buy_out()
        # else:
        #     current_display = 'situation 5'
        #     if current_display != self.display:
        #         self.debug('situation 5')
        #         self.display = current_display

        self.broker.signal('algorithm_trading_table')

    def update_execution_info(self, order):
        # Leverage update
        self.leverage.update(order)

        # Orders update
        if order.open_amount:
            if order.order_position in (PURCHASE, CORRECT_PURCHASE):
                self.orders[ALGORITHM_PURCHASE] = order
            elif order.order_position in (SELL, CORRECT_SELL):
                self.orders[ALGORITHM_SALE] = order

        if order.order_amount == order.executed_amount_sum:
            self.orders[order.order_number] = order

            if order.order_position == PURCHASE and self.orders[ALGORITHM_PURCHASE]:
                del self.orders[ALGORITHM_PURCHASE]
            elif order.order_position == SELL and self.orders[ALGORITHM_SALE]:
                del self.orders[ALGORITHM_SALE]

    def update_balance_info(self, item):
        self.balance_item = item