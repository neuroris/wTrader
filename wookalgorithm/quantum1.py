import copy
from datetime import datetime
from PyQt5.QtCore import QEventLoop
from wookutil import WookUtil, WookLog, wmath
from wookitem import Item, BalanceItem, Order, AlgorithmItem
from wookdata import *
from wookalgorithm.algorithmbase import AlgorithmBase

'''
Quantum algorithm (2021, 03, 06)

Discrete price algorithm using inverse only
1. Overlapping interval
2. Adjust order price when stock price get out of interval range
3. purchase, sale dictionaries
'''

class QuantumAlgorithm1(AlgorithmBase):
    def __init__(self, log):
        super().__init__(log)
        self.log = log
        self.reference_price = 0
        self.buy_limit = 0
        self.loss_limit = 0
        self.situation_processing = False
        self.cancel_completed = False
        self.inverse = None
        # self.episode_count = 110000000
        # self.episode_increase = 20000000
        # self.sale_count = 10000000
        # self.episode_count = 000000
        self.episode_count = 10000000
        self.episode_increase = 10000000
        self.purchase_count = 1000000
        self.sale_count = 2000000

        self.purchase = Order()
        self.sale = Order()

    def start(self, broker, capital, interval, loss_cut):
        # self.inverse = AlgorithmItemEx('252670')
        self.inverse = AlgorithmItem('252670')
        self.inverse.set_broker(broker)
        self.inverse.set_log(self.log)
        self.broker = broker
        self.capital = capital
        self.interval = interval
        self.loss_cut = loss_cut
        self.is_running = True

        # Charting & Monitoring
        broker.go_chart(self.inverse.item_code)
        broker.demand_monitoring_items_info(self.inverse)

        # Open Orders cancellation
        open_orders = list(broker.open_orders.values())
        for order in open_orders:
            self.broker.cancel(order)

        self.post('STARTED')

    def stop(self):
        if not self.is_running:
            return

        self.post('STOPPED')

        # Open Orders cancellation
        open_orders = list(self.broker.open_orders.values())
        for order in open_orders:
            self.broker.cancel(order)

        # Init Fields
        self.orders.clear()
        self.broker = None
        self.inverse = None
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
        self.situation_processing = False
        self.previous_situation = ''
        self.previous_msg = ()

    def resume(self):
        self.is_running = True

    def halt(self):
        self.is_running = False

    def set_reference(self, price):
        self.reference_price = price
        self.buy_limit = self.reference_price - self.interval
        self.loss_limit = self.buy_limit - self.loss_cut

    def shift_reference_up(self):
        self.set_reference(self.reference_price + self.loss_cut)

    def shift_reference_down(self):
        self.set_reference(self.reference_price - self.loss_cut)

    def update_transaction_info(self, item):
        # First time work
        if not self.start_price:
            self.start_time_text = datetime.now().strftime('%H:%M')
            self.start_time = self.to_min_count(self.start_time_text)
            self.start_price = item.current_price
            # reference_price = wmath.get_bottom(item.current_price, self.interval)
            reference_price = item.current_price + self.loss_cut
            self.set_reference(reference_price)
            self.inverse.buy(self.buy_limit, self.capital // item.current_price)
            return

        # Trade
        # if self.sell_off_ordered:
        #     msg = ('sale.ordered:' + str(self.inverse.sale.ordered), 'open_amount:' + str(self.inverse.sale.open_amount))
        #     self.post('(SELL_OFF)', *msg)
        #     if self.inverse.sale.ordered or self.inverse.sale.open_amount:
        #         return
        #     self.sell_off_ordered = False
        if self.situation_processing:
            return

        if item.current_price > self.reference_price:
            self.post('Situation 1')
            self.inverse.cancel_purchases()
            self.inverse.clear_purchases()
            self.inverse.clear_sales()
            self.shift_reference_up()
            self.episode_count += self.episode_increase
            order_amount = self.capital // item.current_price - self.inverse.holding_amount
            self.inverse.buy(self.buy_limit, order_amount)
        elif item.current_price < self.buy_limit:
            self.post('Situation 4')
            self.inverse.cancel_sales()
            self.inverse.clear_purchases()
            self.inverse.clear_sales()
            self.shift_reference_down()
            self.episode_count += self.episode_increase
            self.inverse.sell(self.reference_price, self.inverse.holding_amount)

    def update_execution_info(self, order):
        # Inverse update execution
        self.inverse.update_execution_info(order)

        # Order processing
        executed_amount = abs(order.executed_amount)
        if order.order_position in (PURCHASE, CORRECT_PURCHASE):
            # Algorithm history update
            old_purchase = self.purchase
            self.purchase = copy.deepcopy(order)
            # self.purchase.order_number = self.episode_count + order.order_number
            self.purchase.order_number = self.episode_count + self.purchase_count +order.order_number

            if old_purchase.order_price == order.order_price:
                del self.orders[old_purchase.order_number]
                self.purchase.executed_amount_sum = old_purchase.executed_amount_sum + executed_amount
                if order.order_state == RECEIPT:
                    self.purchase.order_amount = old_purchase.order_amount + order.order_amount
                    self.purchase.open_amount = old_purchase.open_amount + order.open_amount
                elif order.order_state == ORDER_EXECUTED:
                    self.purchase.open_amount -= executed_amount

            self.orders[self.purchase.order_number] = self.purchase

            # Order
            if order.executed_amount:
                self.inverse.sell(self.reference_price, order.executed_amount)
        elif order.order_position in (SELL, CORRECT_SELL):
            # Algorithm history update
            old_sale = self.sale
            self.sale = copy.deepcopy(order)
            # self.sale.order_number = self.episode_count + self.sale_count + order.order_number
            self.sale.order_number = self.episode_count + self.sale_count + order.order_number

            if old_sale.order_price == order.order_price:
                del self.orders[old_sale.order_number]
                self.sale.executed_amount_sum = old_sale.executed_amount_sum + executed_amount
                self.sale.profit = old_sale.profit + order.profit
                if order.order_state == RECEIPT:
                    self.sale.order_amount = old_sale.order_amount + order.order_amount
                    self.sale.open_amount = old_sale.open_amount + order.open_amount
                elif order.order_state == ORDER_EXECUTED:
                    self.sale.open_amount -= executed_amount

            self.orders[self.sale.order_number] = self.sale

            # Order
            if order.executed_amount:
                self.inverse.buy(self.buy_limit, order.executed_amount)
                self.total_profit += order.profit
                self.signal('algorithm_update')

        self.broker.draw_chart.start()

        # if order.order_position in (CANCEL_PURCHASE, CANCEL_SELL) and order.order_state == CONFIRMED:
        #     if not order.executed_amount_sum:
        #         if order.order_number in self.orders:
        #             del self.orders[order.order_number]
        # else:
        #     pass
        #     self.orders[order.order_number] = order

    def display_situation(self, current_situation):
        if current_situation != self.previous_situation:
            self.post(current_situation)
            self.previous_situation = current_situation

    def post(self, *args):
        if args != self.previous_msg:
            self.debug('\033[93mALGORITHM', *args, '\033[97m')
            self.previous_msg = args