import copy
from datetime import datetime
from PyQt5.QtCore import QEventLoop
from wookutil import WookUtil, WookLog, wmath
from wookitem import Item, BalanceItem, Order, AlgorithmItem
from wookdata import *

class AlgorithmBase(WookUtil, WookLog):
    def __init__(self, log):
        WookLog.custom_init(self, log)

        self.broker = None
        self.signal = None
        self.orders = dict()
        self.log = log

        self.is_running = False
        self.episode_count = 0
        self.episode_purchase_number = ''
        self.episode_sale_number = ''
        self.episode_amount = 0

        self.capital = 0
        self.interval = 0
        self.loss_cut = 0
        self.minimum_transaction_amount = 0
        self.start_time_text = ''
        self.start_time = 0
        self.start_price = 0
        self.total_profit = 0
        self.total_fee = 0
        self.net_profit = 0
        self.fee = 0

        self.previous_situation = ''
        self.previous_msg = ()

    def stop(self):
        if not self.is_running:
            return

        # Open Orders cancellation
        open_orders = list(self.broker.open_orders.values())
        for order in open_orders:
            self.broker.cancel(order)

        # Init Fields
        self.orders.clear()
        self.broker = None
        self.is_running = False
        self.episode_count = 0
        self.capital = 0
        self.interval = 0
        self.loss_cut = 0
        self.start_time_text = ''
        self.start_time = 0
        self.start_price = 0
        self.previous_situation = ''
        self.previous_msg = ()

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

    def display_situation(self, current_situation):
        if current_situation != self.previous_situation:
            self.post(current_situation)
            self.previous_situation = current_situation

    def post(self, *args):
        if args != self.previous_msg:
            self.debug('\033[93mALGORITHM', *args, '\033[97m')
            self.previous_msg = args