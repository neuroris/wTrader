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
        self.target_amount = 0
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

class AlgorithmItem(Order, WookLog):
    def __init__(self, item_code):
        super().__init__()
        self.broker = None
        self.item_code = item_code
        self.item_name = CODES[item_code]
        self.purchase = Order()
        self.sale = Order()
        self.purchases = dict()
        self.sales = dict()
        self.purchase_ordered = False
        self.sale_ordered = False
        self.previous_msg = ()

    def set_broker(self, broker):
        self.broker = broker

    def set_log(self, log):
        WookLog.custom_init(self, log)

    def post_cyan(self, *args):
        if args != self.previous_msg:
            self.debug('\033[96mALGORITHM', *args, '\033[97m')
            self.previous_msg = args

    def post_green(self, *args):
        if args != self.previous_msg:
            self.debug('\033[92mALGORITHM', *args, '\033[97m')
            self.previous_msg = args

    def update_execution_info(self, order):
        executed_amount = abs(order.executed_amount)
        if order.order_position in (PURCHASE, CORRECT_PURCHASE):
            self.purchase = order
            self.purchases[order.order_number] = order
            self.purchase.ordered = False
            if order.order_state == ORDER_EXECUTED:
                self.holding_amount += executed_amount
                self.purchase_price = order.executed_price
                self.purchase_sum += executed_amount * order.executed_price
                self.purchase_price_avg = self.purchase_sum / self.holding_amount
        elif order.order_position in (SELL, CORRECT_SELL):
            if order.order_number in self.sales:
                old_order = self.sales[order.order_number]
                order.purchase_price = old_order.purchase_price
            else:
                order.purchase_price = self.purchase_price
            if order.order_state == ORDER_EXECUTED:
                self.holding_amount -= executed_amount
                self.purchase_sum = self.purchase_price_avg * self.holding_amount
                # profit = int((order.executed_price_avg - self.purchase_price_avg) * order.executed_amount)
                # order.profit = self.sale.profit + profit

                order.profit = int((order.executed_price - order.purchase_price) * order.executed_amount)

                # self.profit += profit
                self.profit += order.profit
            self.sale = order
            self.sales[order.order_number] = order
            self.sale.ordered = False
            if not order.open_amount:
                self.sale = Order()

        # Update message
        msg = (order.order_position, order.order_state, 'holding:' + str(self.holding_amount))
        msg += ('order:' + str(order.order_amount), 'executed_each:' + str(order.executed_amount))
        msg += ('open:' + str(order.open_amount), 'number:' + str(order.order_number))
        msg += ('purchase:' + str(order.purchase_price), 'executed:' + str(order.executed_price))
        self.post_green('(EXECUTION)', *msg)

    def buy(self, price, amount, order_type='LIMIT'):
        if self.purchase.ordered:
            return

        msg = ('holding:' + str(self.holding_amount), 'price:' + str(price), 'amount:' + str(amount))
        self.post_cyan('(BUY)', *msg)

        self.purchase.ordered = True
        self.target_amount = amount
        self.broker.buy(self.item_code, price, amount, order_type)

    def buy_over(self, price, amount, order_type='LIMIT'):
        if self.purchase.ordered:
            return

        msg = ('holding:' + str(self.holding_amount), 'open:' + str(self.purchase.open_amount))
        self.post_cyan('(BUY_OVER)', *msg)

        self.purchase.ordered = True
        self.target_amount = amount
        if self.purchase.open_amount:
            self.broker.cancel_and_buy(self.purchase, price, amount, order_type)
        else:
            self.broker.buy(self.item_code, price, amount, order_type)

    def buy_up(self):
        if self.purchase.ordered:
            return

        purchase_amount = self.target_amount - self.holding_amount
        refill_amount = purchase_amount - self.purchase.open_amount

        msg = ('holding:'+str(self.holding_amount), 'order:'+str(self.purchase.order_amount))
        msg += ('open:'+str(self.purchase.open_amount), 'refill:'+str(refill_amount))
        if refill_amount:
            msg = ('\033[94mEXECUTED\033[97m',) + msg
        self.post_cyan('(BUY_UP)', *msg)

        if refill_amount:
            self.purchase.ordered = True
            if self.purchase.open_amount:
                self.broker.cancel_and_buy(self.purchase, self.purchase.order_price, purchase_amount)
            else:
                self.broker.buy(self.item_code, self.purchase.order_price, purchase_amount)

    def sell(self, price, amount, order_type='LIMIT'):
        if not self.holding_amount or self.sale.ordered:
            return

        msg = ('holding:' + str(self.holding_amount), 'price:' + str(price), 'amount:' + str(amount))
        self.post_cyan('(SELL)', *msg)

        self.sale.ordered = True
        self.broker.sell(self.item_code, price, amount, order_type)

    def sell_out(self, price):
        if self.sale.ordered:
            return

        sell_amount = self.holding_amount + self.sale.executed_amount_sum - self.sale.order_amount

        msg = ('holding:'+str(self.holding_amount), 'order:'+str(self.sale.order_amount))
        msg += ('executed:'+str(self.sale.executed_amount_sum), 'open:'+str(self.sale.open_amount))
        msg += ('sell:'+str(sell_amount),)
        if sell_amount:
            msg = ('\033[94mEXECUTED\033[97m',) + msg
        self.post_cyan('(SELL_OUT)', *msg)

        if sell_amount:
            self.sale.ordered = True
            if self.sale.open_amount:
                self.broker.cancel_and_sell(self.sale, price, self.holding_amount)
            else:
                self.broker.sell(self.item_code, price, self.holding_amount)

    def sell_off(self):
        if not self.holding_amount or self.sale.ordered:
            return

        msg = ('holding:' + str(self.holding_amount), 'purchase.open:' + str(self.purchase.open_amount))
        msg += ('sale.open:' + str(self.sale.open_amount),)
        self.post_cyan('(SELL_OFF)', *msg)

        self.sale.ordered = True
        if self.purchase.open_amount:
            self.broker.cancel(self.purchase)
        if self.sale.open_amount:
            self.broker.cancel_and_sell(self.sale, 0, self.holding_amount, 'MARKET')
        else:
            self.broker.sell(self.item_code, 0, self.holding_amount, 'MARKET')

    # def cancel_purchase(self):
    #     self.cancel(self.purchase)
    #
    # def cancel_sale(self):
    #     self.cancel(self.sale)

    def correct(self, order, price, amount=None):
        self.broker.correct(order, price, amount)

    def correct_purchase(self, price):
        if self.purchase.executed_amount_sum:
            self.broker.cancel_and_buy(self.purchase, price)
        else:
            self.broker.correct(self.purchase, price)

    def correct_sale(self, price):
        if self.sale.ordered:
            self.correct(self.sale, price)

    def cancel(self, order):
        self.broker.cancel(order)

    def cancel_purchases(self):
        # new_purchases = dict()
        for order in self.purchases.values():
            if order.open_amount:
                self.cancel(order)
            # else:
            #     new_purchases[order.order_number] = order
        # self.purchases = new_purchases
        # self.clear_purchases()

    def cancel_sales(self):
        # new_sales = dict()
        for order in self.sales.values():
            if order.open_amount:
                self.cancel(order)
            # else:
            #     new_sales[order.order_number] = order
        # self.sales = new_sales
        # self.clear_sales()

    def clear_purchases(self):
        self.purchases.clear()

    def clear_sales(self):
        self.sales.clear()

# class AlgorithmItemEx(AlgorithmItemBase):
#     def __init__(self, item_code):
#         super().__init__()
#         self.item_code = item_code
#         self.item_name = CODES[item_code]
#         self.purchase_ordered = False
#         self.sale_ordered = False
#         self.purchase = dict()
#         self.sale = dict()
#
#     def update_execution_info(self, order):
#         executed_amount = abs(order.executed_amount)
#         if order.order_position in (PURCHASE, CORRECT_PURCHASE):
#             self.purchase[order.order_number] = order
#             # self.purchase_price = order.order_price
#             self.purchase_ordered = False
#             if order.executed_amount:
#                 self.holding_amount += executed_amount
#                 self.purchase_price = order.executed_price
#
#                 # self.purchase_sum += executed_amount * order.executed_price
#                 # self.purchase_price_avg = self.purchase_sum / self.holding_amount
#         elif order.order_position in (SELL, CORRECT_SELL):
#             # Purchase price hand over
#             if order.order_number in self.sale:
#                 old_order = self.sale[order.order_number]
#                 order.purchase_price = old_order.purchase_price
#             else:
#                 order.purchase_price = self.purchase_price
#             self.sale[order.order_number] = order
#             self.sale_ordered = False
#
#             if order.order_state == ORDER_EXECUTED:
#                 self.holding_amount -= executed_amount
#                 # self.purchase_sum = self.purchase_price_avg * self.holding_amount
#                 order.profit = int((order.executed_price - order.purchase_price) * order.executed_amount)
#                 self.profit += order.profit
#
#         # Update message
#         msg = (order.order_position, order.order_state, 'holding:'+str(self.holding_amount))
#         msg += ('order:'+str(order.order_amount), 'executed_each:'+str(order.executed_amount))
#         msg += ('open:'+str(order.open_amount), 'number:'+str(order.order_number))
#         msg += ('purchase:'+str(order.purchase_price), 'executed:'+str(order.executed_price))
#         self.post_green('(EXECUTION)', *msg)
#
#     def buy(self, price, amount, order_type='LIMIT'):
#         # if self.purchase_ordered:
#         #     return
#
#         self.purchase_ordered = True
#         self.target_amount = amount
#         self.broker.buy(self.item_code, price, amount, order_type)
#
#     def sell(self, price, amount, order_type='LIMIT'):
#         # if not self.holding_amount or self.sale_ordered:
#         #     return
#         if not self.holding_amount:
#             return
#
#         self.sale_ordered = True
#         self.broker.sell(self.item_code, price, amount, order_type)
#
#     def cancel(self, order):
#         self.broker.cancel(order)
#
#     def cancel_purchase(self):
#         new_purchase = dict()
#         for order in self.purchase.values():
#             if order.open_amount:
#                 self.cancel(order)
#             else:
#                 new_purchase[order.order_number] = order
#         self.purchase = new_purchase
#
#     def cancel_sale(self):
#         new_sale = dict()
#         for order in self.sale.values():
#             if order.open_amount:
#                 self.cancel(order)
#             else:
#                 new_sale[order.order_number] = order
#         self.sale = new_sale
#
#     def correct(self, order, price, amount=None):
#         self.broker.correct(order, price, amount)