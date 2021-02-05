from wookutil import WookLog
from wookdata import *

class Item:
    def __init__(self):
        self.item_code = ''
        self.item_name = ''
        self.transaction_time = ''
        self.current_price = 0
        self.purchase_price = 0
        self.ask_price = 0
        self.bid_price = 0
        self.open_price = 0
        self.high_price = 0
        self.low_price = 0
        self.reference_price = 0
        self.purchase_price_avg = 0
        self.purchase_sum = 0
        self.purchase_amount = 0
        self.purchase_amount_net_today = 0
        self.order_amount = 0
        self.holding_amount = 0
        self.sellable_amount = 0
        self.volume = 0
        self.accumulated_volume = 0
        self.profit = 0
        self.profit_rate = 0.0
        self.profit_realization = 0
        self.profit_realization_rate = 0.0
        self.purchase_fee = 0
        self.evaluation_fee = 0
        self.transaction_fee = 0
        self.total_fee = 0
        self.tax = 0

class BalanceItem(Item):
    balance_profit_net_today = 0
    balance_profit_rate = 0.0
    balance_profit_realization = 0
    balance_profit_realization_rate = 0.0

    def __init__(self):
        super().__init__()

class Order(Item):
    def __init__(self):
        super().__init__()
        self.order_executed_time = ''
        self.order_state = ''
        self.order_type = ''
        self.order_position = ''
        self.trade_position = ''
        self.order_price = 0
        self.executed_price = 0
        self.executed_price_avg = 0
        self.executed_amount = 0
        self.executed_amount_sum = 0
        self.open_amount = 0
        self.order_number = 0
        self.original_order_number = ''
        self.executed_order_number = 0
        self.ordered = False

class AlgorithmItem(Item, WookLog):
    def __init__(self, item_code):
        super().__init__()
        self.broker = None
        self.item_code = item_code
        self.item_name = CODES[item_code]
        self.purchase = Order()
        self.sale = Order()

    def set_broker(self, broker):
        self.broker = broker

    def set_log(self, log):
        WookLog.custom_init(self, log)

    def update(self, order):
        if order.order_position in (PURCHASE, CORRECT_PURCHASE, CANCEL_PURCHASE):
            if order.order_number < self.purchase.order_number:
                return
        else:
            if order.order_number < self.sale.order_number:
                return

        executed_amount = abs(order.executed_amount)
        if order.order_position == PURCHASE:
            self.purchase = order
            if order.order_state == RECEIPT:
                self.purchase.ordered = False
            if order.order_state == ORDER_EXECUTED:
                self.holding_amount += executed_amount
        elif order.order_position == SELL:
            self.sale = order
            if order.order_state == RECEIPT:
                self.sale.ordered = False
            if order.order_state == ORDER_EXECUTED:
                self.holding_amount -= executed_amount
        elif order.order_position == CORRECT_PURCHASE:
            self.purchase = order
        elif order.order_position == CORRECT_SELL:
            self.sale = order
        elif order.order_position == CANCEL_PURCHASE:
            self.purchase = order
        elif order.order_position == CANCEL_SELL:
            self.sale = order

    def buy(self, price, amount, order_type='LIMIT'):
        if self.purchase.ordered:
            return

        self.purchase.ordered = True
        self.broker.buy(self.item_code, price, amount, order_type)

    def buy_out(self):
        if self.purchase.ordered:
            return

        purchase_amount = self.purchase.order_amount - self.holding_amount
        refill_amount = purchase_amount - self.purchase.open_amount

        self.debug('buy_out', 'order_amount:', self.purchase.order_amount, 'holding_amount:', self.holding_amount, 'open_amount:', self.purchase.open_amount, 'refill_amount:', refill_amount)

        if refill_amount:
            self.purchase.ordered = True
            self.broker.cancel_and_buy(self.purchase, self.purchase.order_price, purchase_amount)

    def sell(self, price, amount, order_type='LIMIT'):
        if not self.holding_amount or self.sale.ordered:
            return

        self.sale.ordered = True
        self.broker.sell(self.item_code, price, amount, order_type)

    def sell_out(self, price):
        if self.sale.ordered:
            return

        sell_amount = self.holding_amount - self.sale.order_amount

        self.debug('sell_out', 'holding_amount:', self.holding_amount, 'order_amount:', self.sale.order_amount, 'sell_amount:', sell_amount, self.sale.ordered)


        if sell_amount:
            self.sale.ordered = True
            if self.sale.order_number:
                self.broker.cancel_and_sell(self.sale, price, self.holding_amount)
            else:
                self.sell(price, self.holding_amount)

    def sell_off(self):
        if not self.holding_amount or self.sale.ordered:
            return

        self.debug('sell_off', 'holding_amount:', self.holding_amount, 'open_amount:', self.sale.open_amount, self.sale.ordered)

        self.sale.ordered = True
        if self.sale.open_amount:
            self.broker.cancel_and_sell(self.sale, 0, self.holding_amount, 'MARKET')
        else:
            self.sell(0, self.holding_amount, 'MARKET')

    def cancel(self, order):
        self.broker.cancel(order)

    def cancel_purchase(self):
        self.cancel(self.purchase)

    def cancel_sale(self):
        self.cancel(self.sale)

    def correct(self, order, price, amount=None):
        self.broker.correct(order, price, amount)

    def correct_purchase(self, price):
        self.correct(self.purchase, price)

    def correct_sale(self, price):
        if self.sale.ordered:
            self.correct(self.sale, price)

class OrderManager:
    def __init__(self):
        self.orders = dict()

    def add(self, order):
        self.orders[order.order_number] = order

    def remove(self, order):
        del self.orders[order.order_number]

    def get_order_amount(self):
        order_amount = 0
        for order in self.orders.values():
            order_amount += order.order_amount
        return order_amount

    def get_open_amount(self):
        open_amount = 0
        for order in self.orders.values():
            open_amount += order.open_amount
        return open_amount

    def get_executed_amount(self):
        executed_amount = 0
        for order in self.orders.values():
            executed_amount += order.executed_amount_sum
        return executed_amount