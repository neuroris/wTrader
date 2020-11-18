from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QThread
from PyQt5.QtTest import QTest
from queue import Queue
import time, os, re
import pickle
from wookutil import WookCipher, WookLog, WookTimer
from wookdata import *

class KiwoomBase(QAxWidget, WookLog):
    def __init__(self, log, key):
        super().__init__('KHOPENAPI.KHOpenAPICtrl.1')
        WookLog.custom_init(self, log)

        wc = WookCipher(key)
        wc.decrypt_data()
        self.login_id = wc.login_id
        self.login_password = wc.login_password
        self.account_password = wc.account_password
        self.certificate_password = wc.certificate_password

        self.event_loop = QEventLoop()
        self.login_event_loop = QEventLoop()

        self.timer_event_loop = QEventLoop()
        self.timer = WookTimer(self.timer_event_loop)

        self.signal = None
        self.status = None
        self.login_status = None

        self.screen_no_account = '0010'
        self.screen_no_inconclusion = '0020'
        self.screen_no_stock_price = '0030'
        self.screen_no_operation_state = '0040'
        self.screen_no_interesting_items = '0050'
        self.screen_no_bid = '0060'

        self.account_list = None
        self.account_number = 0
        self.deposit = 0
        self.withdrawable = 0
        self.purchase_total_sum = 0
        self.profit_evaluated_sum = 0
        self.profit_rate_sum = 0
        self.item_code = 0
        self.item_name = ''
        self.first_day = ''
        self.last_day = ''
        self.save_folder = ''
        self.working_date = 0
        self.tick_type = ''
        self.min_type = ''
        self.day_type = ''
        self.stock_prices = list()

        self.stocks = list()
        self.portfolio_stocks = list()
        self.interesting_stocks = list()
        self.unconcluded_stocks = list()

        self.previous_time = 0.0
        self.reference_time = Queue()
        self.consecutive_interval_limit = 0.25
        self.request_block_time_limit = 5
        self.request_block_size = 10
        self.request_count = 0
        self.request_count_threshold = 90
        self.request_count_interval = 60
        self.request_count_waiting = 30

        self.interesting_stocks_file = 'interesting_stocks.bin'

    def load_interesting_stocks(self):
        if not os.path.exists(self.interesting_stocks_file):
            print('interesting_stocks file not exist')
            return

        with open(self.interesting_stocks_file, 'rb') as file:
            self.interesting_stocks = pickle.load(file)
        print(self.interesting_stocks)

    def save_intesting_stocks(self):
        with open(self.interesting_stocks_file, 'wb') as file:
            pickle.dump(self.interesting_stocks, file)

    def dynamic_call(self, function_name, *args):
        function_spec = '('
        for order in range(len(args)):
            parameter = 'parameter_' + str(order)
            function_spec += parameter
            if order < len(args) - 1:
                function_spec += ', '
        function_spec += ')'
        function_spec = function_name + function_spec
        args = list(args)
        result = self.dynamicCall(function_spec, args)
        return result

    def set_input_value(self, item, value):
        self.dynamicCall('SetInputValue(str, str)', item, value)

    def set_input_values(self, account_number=None, account_password=None, media_type='00', inquiry_type='1'):
        if account_number is None: account_number = self.account_number
        if account_password is None: account_password = self.account_password

        self.set_input_value(ACCOUNT_NUMBER, account_number)
        self.set_input_value(PASSWORD, account_password)
        self.set_input_value(PASSWORD_MEDIA_TYPE, media_type)
        self.set_input_value(INQUIRY_TYPE, inquiry_type)

    def comm_rq_data(self, sRQName, sTrCode, sPrevNext, sScreenNo):
        self.check_time_rule()
        result = self.dynamicCall('CommRqData(str, str, int, str)', sRQName, sTrCode, sPrevNext, sScreenNo)
        if result != 0:
            print('Something is wrong during request : {}, Error code : {}'.format(sRQName, result))

    def get_comm_data(self, sTrCode, sRQName, nIndex, strItemName):
        result = self.dynamicCall('GetCommData(str, str, int, str)', sTrCode, sRQName, nIndex, strItemName)
        processed_result = self.process_type(result)
        return processed_result

    def get_comm_data_ex(self, sTrCode, sRQName):
        result = self.dynamic_call('GetCommDataEx', sTrCode, sRQName)
        return result

    def new_get_comm_data(self, *precedent_args):
        def custom_get_comm_data(*args):
            new_args = precedent_args + args
            result = self.get_comm_data(*new_args)
            return result
        return custom_get_comm_data

    def get_repeat_count(self, sTrCode, sRQName):
        repeat_count = self.dynamic_call('GetRepeatCnt', sTrCode, sRQName)
        return repeat_count

    def set_real_reg(self, strScreenNo, strCodeList, strFidList, strOptType='1'):
        self.dynamic_call('SetRealReg', strScreenNo, strCodeList, strFidList, strOptType)

    def get_comm_real_data(self, sCode, fid):
        result = self.dynamic_call('GetCommRealData', sCode, fid)
        processed_result = self.process_type(result)
        return processed_result

    def new_get_comm_real_data(self, *precedent_args):
        def custom_get_comm_real_data(*args):
            new_args = precedent_args + args
            result = self.get_comm_real_data(*new_args)
            return result
        return custom_get_comm_real_data

    def send_order(self, sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice, sHogaGb, sOrgOrderNo=''):
        result = self.dynamic_call('SendOrder', sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice, sHogaGb, sOrgOrderNo)
        return result

    def new_send_order(self, *precedent_args):
        def custom_send_order(*args):
            new_args = precedent_args + args
            result = self.send_order(*new_args)
            return result
        return custom_send_order

    def get_chejan_data(self, nFid):
        result = self.dynamic_call('GetChejanData', nFid)
        processed_result = self.process_type(result)
        return processed_result

    def check_time_rule(self):
        # consecutive 28 request is blocked in 5 times a sec
        # consecutive 100 request is blocked in 4 times a sec
        # every 25 request, 10 sec waiting is required optimally
        time_interval = time.time() - self.previous_time
        if time_interval < self.consecutive_interval_limit:
            waiting_time = self.consecutive_interval_limit - time_interval
            time.sleep(waiting_time)

        if self.reference_time.qsize() == self.request_block_size:
            reference_time = self.reference_time.get()
        else:
            reference_time = 0
        reference_time_interval = time.time() - reference_time

        if reference_time_interval < self.request_block_time_limit:
            waiting_time = self.request_block_time_limit - reference_time_interval
            self.info('now waiting {}s... for request block interval'.format(waiting_time))
            time.sleep(waiting_time)

        if self.request_count >= self.request_count_threshold:
            if (self.request_count - self.request_count_threshold) % self.request_count_interval == 0:
                print('now waiting {}s... for request count over {}'.format(self.request_count_waiting,
                                                                            self.request_count))
                self.sleep(self.request_count_waiting)

        self.signal('Request count', self.request_count + 1)
        self.signal('Reference time interval', reference_time_interval)

        self.request_count += 1
        current_time = time.time()
        self.previous_time = current_time
        self.reference_time.put(current_time)

    def sleep(self, time):
        self.timer.sleep(time)
        self.timer.start()
        self.timer_event_loop.exec()

    def process_type(self, data):
        data = data.strip()
        int_criteria = re.compile('([+]{0,1}|[-]{0,1})\d+$')
        if int_criteria.match(data):
            return int(data)

        float_criteria = re.compile('([+]{0,1}|[-]{0,1})\d+[.]\d+$')
        if float_criteria.match(data):
            return float(data)

        return data

    def formalize_int(self, str_data):
        int_data = int(str_data)
        formalized_data = format(int_data, ',')
        return formalized_data

    def formalize_float(self, str_data):
        float_data = float(str_data)
        formalized_data = format(float_data, ',')
        return formalized_data