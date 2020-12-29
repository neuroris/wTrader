class Stock:
    balance_profit_net_today = 0
    balance_profit_rate = 0.0
    balance_profit_realization = 0
    balance_profit_realization_rate = 0.0

    def __init__(self):
        self.item_code = ''
        self.item_name = ''
        self.transaction_time = ''
        self.order_executed_time = ''
        self.order_state = ''
        self.order_type = ''
        self.order_position = ''
        self.trade_position = ''
        self.current_price = 0
        self.purchase_price = 0
        self.ask_price = 0
        self.bid_price = 0
        self.high_price = 0
        self.low_price = 0
        self.order_price = 0
        self.executed_price = 0
        self.open_price = 0
        self.reference_price = 0
        self.purchase_price_avg = 0
        self.purchase_sum = 0
        self.purchase_amount = 0
        self.purchase_amount_net_today = 0
        self.order_amount = 0
        self.executed_amount = 0
        self.open_amount = 0
        self.holding_amount = 0
        self.sellable_amount = 0
        self.volume = 0
        self.accumulated_volume = 0
        self.order_number = 0
        self.original_order_number = 0
        self.executed_order_number = 0
        self.deposit = 0
        self.profit = 0
        self.profit_rate = 0.0
        self.profit_realization = 0
        self.profit_realization_rate = 0.0
        self.purchase_fee = 0
        self.evaluation_fee = 0
        self.transaction_fee = 0
        self.total_fee = 0
        self.tax = 0

class StockManager:
    def __init__(self):
        self.stocks = dict()

    def hold(self, given_stock):
        for order_price, stock in self.stocks.items():
            if order_price == given_stock.order_price:
                if stock.item_code == given_stock.item_code:
                    return True
        return False

    def add_stock(self, given_stock):
        if not self.hold(given_stock):
            self.stocks[given_stock.order_price] = given_stock
            return

        stock = self.stocks[given_stock.order_price]
        stock.item_name = given_stock.item_name
        stock.current_price = given_stock.current_price
        stock.order_price = given_stock.order_price
        stock.executed_price = given_stock.executed_price
        stock.order_amount = given_stock.order_amount
        stock.executed_amount = given_stock.executed_amount
        stock.open_amount = given_stock.open_amount
        stock.order_number = given_stock.order_number

    def remove_stock(self, stock):
        del self.stocks[stock.order_price]

    def get_stocks(self):
        return self.stocks