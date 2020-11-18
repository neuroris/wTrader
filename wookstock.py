import unicodedata
from wookdata import *

class Stock:
    def __init__(self):
        self.item_number = ''
        self.item_code = ''
        self.item_name = ''
        self.order_state = ''
        self.order_type = ''
        self.order_number = 0
        self.order_amount = 0
        self.order_price = 0
        self.unconcluded_amount = 0
        self.concluded_amount = 0
        self.purchase_amount = 0
        self.purchase_price = 0
        self.current_price = 0
        self.purchase_sum = 0
        self.profit_rate = 0.0
        self.sellable_amount = 0

        self.item_number_len = 8
        self.item_name_len = 20
        self.purchase_amount_len = 8
        self.purchase_price_len = 10
        self.current_price_len = 10
        self.purchase_sum_len = 15
        self.profit_rate_len = 12
        self.sellable_amount_len = 8

        self.arranged_str = ''

    def get_header(self):
        self.set_str()
        self.set_str(ITEM_NUMBER, self.item_number_len)
        self.set_str(ITEM_NAME, self.item_name_len)
        self.set_str(PURCHASE_AMOUNT, self.purchase_amount_len)
        self.set_str(PURCHASE_PRICE, self.purchase_price_len)
        self.set_str(CURRENT_PRICE, self.current_price_len)
        self.set_str(PURCHASE_SUM, self.purchase_sum_len)
        self.set_str(PROFIT_RATE, self.profit_rate_len)
        self.set_str(SELLABLE_AMOUNT, self.sellable_amount_len)
        header = self.get_arranged_str()
        return header

    def get_arranged_info(self):
        self.set_str()
        self.set_str(self.item_number, self.item_number_len)
        self.set_str(self.item_name, self.item_name_len)
        self.set_str(self.purchase_amount, self.purchase_amount_len)
        self.set_str(self.purchase_price, self.purchase_price_len)
        self.set_str(self.current_price, self.current_price_len)
        self.set_str(self.purchase_sum, self.purchase_sum_len)
        self.set_str(self.profit_rate, self.profit_rate_len)
        self.set_str(self.sellable_amount, self.sellable_amount_len)
        item_data = self.get_arranged_str()
        return item_data

    def formalize_str(self, text, max_length):
        text_length = 0
        for character in text:
            code = unicodedata.east_asian_width(character)
            if code in ('F', 'W'):
                text_length += 1.625
            else:
                text_length += 1

        blank_length = round(max_length - text_length)
        reform_text = text + ' ' * blank_length
        return reform_text

    def set_str(self, data=None, max_length=None):
        if data is None:
            self.format_str = ''
            return

        if type(data) is not str:
            data = format(data, ',')

        new_text = self.formalize_str(data, max_length)
        self.format_str += new_text

    def get_arranged_str(self):
        return self.format_str