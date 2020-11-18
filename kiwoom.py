from kiwoombase import KiwoomBase
from wookauto import LoginPasswordThread, AccountPasswordThread
from wookdata import *

class Kiwoom(KiwoomBase):
    def __init__(self, log, key):
        super().__init__(log, key)
        self.info('Kiwoom initializing...')
        self.count = 0

        # Connect slots
        self.OnEventConnect.connect(self.on_login)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveMsg.connect(self.on_receive_msg)
        self.OnReceiveConditionVer.connect(self.on_receive_condition_ver)

    def connect(self, auto_login):
        if auto_login:
            self.auto_login()
        else:
            self.login()
            self.set_account_password()
        self.info('Logged in to Kiwoom server')
        self.get_account_list()

        return self.login_status

    def auto_login(self):
        self.dynamicCall('CommConnect()')
        self.login_event_loop.exec()

    def login(self):
        self.dynamicCall("CommConnect()")
        log_passwd_thread = LoginPasswordThread(self.event_loop, self.login_id, self.login_password, self.certificate_password)
        log_passwd_thread.start()
        self.event_loop.exec()
        self.login_event_loop.exec()

    def set_account_password(self):
        acc_psword_thread = AccountPasswordThread(self.event_loop, self.account_password)
        acc_psword_thread.start()
        self.event_loop.exec()

        # self.KOA_Functions('ShowAccountWindow', '')

    def get_account_list(self):
        self.info('Getting account infomation...')
        account_list = self.dynamic_call('GetLoginInfo()', 'ACCLIST')
        self.account_list = account_list.split(';')
        self.account_list.pop()

        for index, account in enumerate(self.account_list):
            self.debug("Account {} : {}".format(index+1, account))

    def request_stock_price_tick(self, sPrevNext='0'):
        self.set_input_value(ITEM_CODE, self.item_code)
        self.set_input_value(TICK_RANGE, self.tick_type)
        self.set_input_value(CORRECTED_PRICE_TYPE, '1')
        self.comm_rq_data('stock price tick', REQUEST_TICK_PRICE, sPrevNext, self.screen_no_stock_price)
        self.event_loop.exec()

    def request_stock_price_min(self, sPrevNext='0'):
        self.set_input_value(ITEM_CODE, self.item_code)
        self.set_input_value(TICK_RANGE, self.min_type)
        self.set_input_value(CORRECTED_PRICE_TYPE, '1')
        self.comm_rq_data('stock price min', REQUEST_MINUTE_PRICE, sPrevNext, self.screen_no_stock_price)
        self.event_loop.exec()

    def request_stock_price_day(self, sPrevNext='0'):
        request = self.get_day_request_type()
        self.set_input_value(ITEM_CODE, self.item_code)
        self.set_input_value(REFERENCE_DATE, self.last_day.replace('-', ''))
        self.set_input_value(END_DATE, self.first_day.replace('-', ''))
        self.set_input_value(CORRECTED_PRICE_TYPE, '1')
        self.comm_rq_data('stock price day', request, sPrevNext, self.screen_no_stock_price)
        self.event_loop.exec()

    def finish_stock_price_request(self, type):
        self.request_count = 0
        self.working_date = 0
        self.stock_prices.clear()
        self.status('Getting stock price ({}) done'.format(type[12:]))
        self.info('Getting stock price ({}) done'.format(type[12:]))
        self.init_screen_no(self.screen_no_stock_price)
        self.event_loop.exit()

    def on_login(self, err_code):
        self.login_status = err_code
        self.info('Login status code :', err_code)
        self.login_event_loop.exit()

    def on_receive_tr_data(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        if sRQName == 'stock price tick':
            self.get_stock_price_tick(sTrCode, sRQName, sPrevNext)
        elif sRQName == 'stock price min':
            self.get_stock_price_min(sTrCode, sRQName, sPrevNext)
        elif sRQName == 'stock price day':
            self.get_stock_price_day(sTrCode, sRQName, sPrevNext)

    def on_receive_msg(self, sScrNo, sRQName, sTrCode, sMsg):
        print('Receiving message', sScrNo, sRQName, sTrCode, sMsg)

    def get_stock_price_tick(self, sTrCode, sRQName, sPrevNext):
        get_comm_data = self.new_get_comm_data(sTrCode, sRQName)
        number_of_item = self.get_repeat_count(sTrCode, sRQName)
        first_day = int(self.first_day.replace('-', ''))
        last_day = int(self.last_day.replace('-', ''))

        for count in range(number_of_item):
            transaction_time = str(get_comm_data(count, TRANSACTION_TIME))
            current_date = int(transaction_time[:8])
            if current_date > last_day:
                continue

            # After getting whole day data, save as file
            if self.working_date != current_date:
                if self.working_date != 0:
                    header = 'Transaction time, opening, highest, lowest, current, amount'
                    self.stock_prices.append(header)
                    self.stock_prices.reverse()
                    file_data = '\n'.join(self.stock_prices)
                    saving_file_name = self.save_folder + self.item_name + ' tick ' + str(self.working_date) + '.csv'
                    with open(saving_file_name, 'w') as saving_file:
                        saving_file.write(file_data)
                    self.stock_prices.clear()
                self.working_date = current_date

            if current_date < first_day:
                self.finish_stock_price_request(sRQName)
                return

            opening_price = str(abs(get_comm_data(count, OPENING_PRICE)))
            highest_price = str(abs(get_comm_data(count, HIGHEST_PRICE)))
            lowest_price = str(abs(get_comm_data(count, LOWEST_PRICE)))
            current_price = str(abs(get_comm_data(count, CURRENT_PRICE)))
            concluded_amount = str(abs(get_comm_data(count, TRANSACTION_AMOUNT)))

            time = transaction_time + '_'
            data = [time, opening_price, highest_price, lowest_price, current_price, concluded_amount]
            csv_data = ','.join(data)
            self.stock_prices.append(csv_data)
            self.debug(csv_data)

        if sPrevNext == '2':
            self.request_stock_price_tick(sPrevNext)
        else:
            self.finish_stock_price_request(sRQName)

    def get_stock_price_min(self, sTrCode, sRQName, sPrevNext):
        get_comm_data = self.new_get_comm_data(sTrCode, sRQName)
        number_of_item = self.get_repeat_count(sTrCode, sRQName)
        first_day = int(self.first_day.replace('-',''))
        last_day = int(self.last_day.replace('-',''))

        for count in range(number_of_item):
            transaction_time = str(get_comm_data(count, TRANSACTION_TIME))
            current_date = int(transaction_time[:8])
            if current_date > last_day:
                continue

            # After getting whole day data, save as file
            if self.working_date != current_date:
                if self.working_date != 0:
                    header = 'Transaction time, opening, highest, lowest, current, amount'
                    self.stock_prices.append(header)
                    self.stock_prices.reverse()
                    file_data = '\n'.join(self.stock_prices)
                    saving_file_name = self.save_folder + self.item_name + ' min ' + str(self.working_date) + '.csv'
                    with open(saving_file_name, 'w') as saving_file:
                        saving_file.write(file_data)
                    self.stock_prices.clear()
                self.working_date = current_date

            if current_date < first_day:
                self.finish_stock_price_request(sRQName)
                return

            opening_price = str(abs(get_comm_data(count, OPENING_PRICE)))
            highest_price = str(abs(get_comm_data(count, HIGHEST_PRICE)))
            lowest_price = str(abs(get_comm_data(count, LOWEST_PRICE)))
            current_price = str(abs(get_comm_data(count, CURRENT_PRICE)))
            transaction_amount = str(abs(get_comm_data(count, TRANSACTION_AMOUNT)))

            time = transaction_time[:-2] + '_'
            data = [time, opening_price, highest_price, lowest_price, current_price, transaction_amount]
            csv_data = ','.join(data)
            self.stock_prices.append(csv_data)
            self.debug(csv_data)

        if sPrevNext == '2':
            self.request_stock_price_min(sPrevNext)
        else:
            self.finish_stock_price_request(sRQName)

    def get_stock_price_day(self, sTrCode, sRQName, sPrevNext):
        get_comm_data = self.new_get_comm_data(sTrCode, sRQName)
        number_of_item = self.get_repeat_count(sTrCode, sRQName)
        first_day = int(self.first_day.replace('-', ''))

        for count in range(number_of_item):
            transaction_date = get_comm_data(count, DATE)
            if transaction_date < first_day:
                self.save_stock_price_day(str(self.working_date))
                self.finish_stock_price_request(sRQName)
                return
            self.working_date = transaction_date

            opening_price = str(abs(get_comm_data(count, OPENING_PRICE)))
            highest_price = str(abs(get_comm_data(count, HIGHEST_PRICE)))
            lowest_price = str(abs(get_comm_data(count, LOWEST_PRICE)))
            current_price = str(abs(get_comm_data(count, CURRENT_PRICE)))
            transaction_amount = str(abs(get_comm_data(count, TRANSACTION_AMOUNT)))

            date = str(transaction_date) + '_'
            data = [date, opening_price, highest_price, lowest_price, current_price, transaction_amount]
            csv_data = ','.join(data)
            self.stock_prices.append(csv_data)
            self.debug(csv_data)

        if sPrevNext == '2':
            self.request_stock_price_day(sPrevNext)
        else:
            self.save_stock_price_day(str(transaction_date))
            self.finish_stock_price_request(sRQName)

    def get_day_request_type(self):
        if self.day_type == DAY_DATA:
            return REQUEST_DAY_PRICE
        elif self.day_type == WEEK_DATA:
            return REQUEST_WEEK_PRICE
        elif self.day_type == MONTH_DATA:
            return REQUEST_MONTH_PRICE
        elif self.day_type == YEAR_DATA:
            return REQUEST_YEAR_PRICE

    def save_stock_price_day(self, first_day):
        last_day = self.last_day.replace('-', '')
        header = 'Transaction date, opening, highest, lowest, current, amount'
        self.stock_prices.append(header)
        self.stock_prices.reverse()
        file_data = '\n'.join(self.stock_prices)
        day = first_day + '-' + last_day
        saving_file_name = self.save_folder + self.item_name + ' ' + self.day_type + ' ' + day + '.csv'
        with open(saving_file_name, 'w') as saving_file:
            saving_file.write(file_data)

    def init_screen_no(self, sScrNo):
        self.dynamic_call('DisconnectRealData', sScrNo)

    def on_receive_condition_ver(self, IRet, sMsg):
        print(IRet, sMsg)
        print('receive condition ver')

    def close_process(self):
        pass
        # self.save_intesting_stocks()
        # self.dynamic_call('SetRealRemove', 'ALL', 'ALL')