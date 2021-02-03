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

class AlgorithmItem(Item):
    def __init__(self, item_code):
        super().__init__()
        self.broker = None
        self.item_code = item_code
        self.item_name = CODES[item_code]
        # self.purchase = OrderManager()
        # self.sale = OrderManager()
        self.buy_order = None
        self.sell_order = None
        self.buy_ordered = False
        self.sell_ordered = False

    def set_broker(self, broker):
        self.broker = broker

    def update(self, order):
        executed_amount = abs(order.executed_amount)
        if order.order_position == PURCHASE:
            self.buy_order = order
            if order.order_state == ORDER_EXECUTED:
                self.holding_amount += executed_amount
                if not order.open_amount:
                    self.buy_order = None
                    self.buy_ordered = False
        elif order.order_position == SELL:
            self.sell_order = order
            if order.order_state == ORDER_EXECUTED:
                self.holding_amount -= executed_amount
                if not order.open_amount:
                    self.sell_order = None
                    self.sell_ordered = False
        elif order.order_position == CORRECT_PURCHASE:
            self.buy_order = order
        elif order.order_position == CORRECT_SELL:
            self.sell_order = order
        elif order.order_position == CANCEL_PURCHASE and order.original_order_number == 0:
            self.buy_order = None
        elif order.order_position == CANCEL_SELL and order.original_order_number == 0:
            self.sell_order = None

    def buy(self, price, amount, order_type='LIMIT'):
        if self.buy_ordered:
            return

        self.broker.buy(self.item_code, price, amount, order_type)
        self.buy_ordered = True

    def buy_out(self):
        if self.buy_ordered:
            return

        purchase_amount = self.buy_order.order_amount - self.holding_amount
        refill_amount = purchase_amount - self.buy_order.open_amount
        if refill_amount:
            self.broker.cancel_and_buy(self.buy_order, self.buy_order.order_price, purchase_amount)
            self.buy_ordered = True

    def sell(self, price, amount, order_type='LIMIT'):
        if not self.holding_amount or self.sell_ordered:
            return

        self.broker.sell(self.item_code, price, amount, order_type)
        self.sell_ordered = True

    def sell_out(self, price):
        if not self.sell_order or self.sell_ordered:
            return

        sell_amount = self.holding_amount - self.sell_order.order_amount
        if sell_amount:
            if self.sell_order.order_number:
                self.broker.cancel_and_sell(self.sell_order, price, self.holding_amount)
                self.sell_ordered = True
            else:
                self.sell(price, self.holding_amount)

    def sell_off(self):
        if self.sell_order.order_number:
            self.broker.cancel_and_sell(self.sell_order, 0, self.holding_amount, 'MARKET')
        else:
            self.sell(0, self.holding_amount, 'MARKET')

    def cancel(self, order):
        self.broker.cancel(order)

    def cancel_purchase(self):
        self.cancel(self.buy_order)

    def cancel_sale(self):
        self.cancel(self.sell_order)

    def correct(self, order, price, amount=None):
        self.broker.correct(order, price, amount)

    def correct_purchase(self, price):
        self.correct(self.buy_order, price)

    def correct_sale(self, price):
        if self.sell_ordered:
            self.correct(self.sell_order, price)

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