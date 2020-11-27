from PyQt5.QtWidgets import QTableWidgetItem
from datetime import datetime
from kiwoombase import KiwoomBase
from wookauto import LoginPasswordThread, AccountPasswordThread
from wookstock import Stock
from wookdata import *

class Kiwoom(KiwoomBase):
    def __init__(self, log, key):
        super().__init__(log, key)
        self.debug('Kiwoom initializing...')

        # Connect slots
        self.OnEventConnect.connect(self.on_login)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveRealData.connect(self.on_receive_real_data)
        self.OnReceiveChejanData.connect(self.on_receive_chejan_data)
        self.OnReceiveMsg.connect(self.on_receive_msg)
        self.OnReceiveConditionVer.connect(self.on_receive_condition_ver)

        self.demand_market_state_info()
        # self.request_concluded_order_info()

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
        account_list = self.dynamic_call('GetLoginInfo()', 'ACCLIST')
        self.account_list = account_list.split(';')
        self.account_list.pop()
        if self.account_list is None:
            self.signal('Failed to get account information')
        else:
            self.signal('Account information acquired')
            for index, account in enumerate(self.account_list):
                self.debug("Account {} : {}".format(index+1, account))
        return self.account_list

    def request_deposit_info(self, sPrevNext='0'):
        self.set_input_value(ACCOUNT_NUMBER, self.account_number)
        self.set_input_value(PASSWORD, self.account_password)
        self.set_input_value(PASSWORD_MEDIA_TYPE, '00')
        self.set_input_value(INQUIRY_TYPE, '1')
        self.comm_rq_data('deposit', REQUEST_DEPOSIT_INFO, sPrevNext, self.screen_account)
        self.event_loop.exec()

    def request_portfolio_info(self, sPrevNext='0'):
        self.set_input_value(ACCOUNT_NUMBER, self.account_number)
        self.set_input_value(PASSWORD, self.account_password)
        self.set_input_value(PASSWORD_MEDIA_TYPE, '00')
        self.set_input_value(INQUIRY_TYPE, '1')
        self.comm_rq_data('portfolio', REQUEST_PORTFOLIO_INFO, sPrevNext, self.screen_portfolio)
        self.event_loop.exec()

    def request_concluded_order_info(self, item_code, sPrevNext='0'):
        self.set_input_value(ACCOUNT_NUMBER, self.account_number)
        self.set_input_value(ALL_OR_INDIVIDUAL, INDIVIDUAL)
        self.set_input_value(TRADING_TYPE, ALL)
        self.set_input_value(ITEM_CODE, item_code)
        self.set_input_value(CONCLUSION_TYPE, ALL)
        self.comm_rq_data('conclusion', REQUEST_UNCONCLUDED_ORDER, sPrevNext, self.screen_no_inconclusion)
        self.event_loop.exec()

    def demand_market_state_info(self):
        self.set_real_reg(self.screen_operation_state, ' ', FID.MARKET_OPERATION_STATE, '0')

    def demand_trading_item_info(self, item_code):
        self.set_real_reg(item_code, item_code, FID.TRANSACTION_TIME, '1')

    def on_login(self, err_code):
        self.debug('Login status code :', err_code)
        if err_code == 0:
            self.signal('Kiwoom log in success')
        else:
            self.signal('Something is wrong during log-in')
            self.error('Login error', login_status)
        self.login_event_loop.exit()

    def on_receive_msg(self, sScrNo, sRQName, sTrCode, sMsg):
        self.inquiry_count += 1
        time = datetime.now().strftime('%H:%M:%S')
        self.status(sMsg, sRQName, time, '('+str(self.inquiry_count)+')')
        self.debug('Received message:', sRQName, sMsg)

    def on_receive_tr_data(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        self.debug('tr data', sScrNo, sRQName, sTrCode)
        if sRQName == 'deposit':
            self.get_deposit_info(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'portfolio':
            self.get_portfolio_info(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'conclusion':
            self.get_concluded_order_info(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'order':
            pass

    def on_receive_real_data(self, sCode, sRealType, sRealData):
        self.debug('real', sCode, sRealType, sRealData)
        if sRealType == REAL_TYPE_STOCK_TRADED:
            self.update_trading_items(sCode)
        elif sRealType == REAL_TYPE_MARKET_OPENING_TIME:
            self.update_market_state(sCode)
        elif sRealType == REAL_TYPE_BALANCE:
            self.update_portfolio(sCode)

    def on_receive_chejan_data(self, sGubun, nItemCnt, nFidList):
        self.debug('chejan', sGubun, nItemCnt, nFidList)
        if sGubun == CHEJAN_GUBUN_ORDER_CONCLUSION:
            self.obtain_order_info()
        elif sGubun == CHEJAN_GUBUN_BALANCE:
            self.obtain_balance_info()

    def get_deposit_info(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        get_comm_data = self.new_get_comm_data(sTrCode, sRecordName, 0)
        self.deposit = self.formalize_int(get_comm_data(DEPOSIT))
        self.withdrawable = self.formalize_int(get_comm_data(WITHDRAWABLE))
        self.orderable = self.formalize_int(get_comm_data(ORDERABLE))
        self.debug('Deposit', self.deposit)
        self.signal('Deposit information acquired')
        self.init_screen(sScrNo)
        self.event_loop.exit()

    def get_portfolio_info(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        number_of_item = self.get_repeat_count(sTrCode, sRecordName)
        for count in range(number_of_item):
            get_comm_data = self.new_get_comm_data(sTrCode, sRecordName, count)

            stock = Stock()
            stock.item_code = get_comm_data(ITEM_NUMBER)
            stock.item_name = get_comm_data(ITEM_NAME)
            stock.purchase_price = get_comm_data(PURCHASE_PRICE)
            stock.profit = get_comm_data(PROFIT)
            stock.profit_rate = get_comm_data(PROFIT_RATE)
            stock.purchase_amount = get_comm_data(PURCHASE_AMOUNT)
            stock.current_price = get_comm_data(CURRENT_PRICE)
            stock.purchase_sum = get_comm_data(PURCHASE_SUM)
            stock.evaluation_sum = get_comm_data(EVALUATION_SUM)
            stock.evaluation_fee = get_comm_data(EVALUATION_FEE)
            stock.tax = get_comm_data(TAX)
            stock.sellable_amount = get_comm_data(SELLABLE_AMOUNT)
            self.portfolio[stock.item_code] = stock

        self.display_portfolio_table()
        self.signal('Portfolio information acquired')

        if sPrevNext == '2':
            self.request_portfolio_info(sPrevNext)
        else:
            self.init_screen(sScrNo)
            self.event_loop.exit()

    def get_concluded_order_info(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        self.event_loop.exit()

    def update_market_state(self, sCode):
        operation_state = self.get_comm_real_data(sCode, FID.MARKET_OPERATION_STATE)
        present_time = self.get_comm_real_data(sCode, FID.TRANSACTION_TIME, time=True)
        remaining_time = self.get_comm_real_data(sCode, FID.MARKET_OPERATION_REMAINING_TIME, time=True)

        self.info('market operation state', operation_state, present_time, remaining_time)

    def update_trading_items(self, sCode):
        stock = self.trading_items[sCode]
        get_comm_real_data = self.new_get_comm_real_data(sCode)

        stock.transaction_time = get_comm_real_data(FID.TRANSACTION_TIME)
        stock.current_price = get_comm_real_data(FID.CURRENT_PRICE)
        stock.price_increase_amount = get_comm_real_data(FID.PRICE_INCREASE_AMOUNT)
        stock.price_increase_ratio = get_comm_real_data(FID.PRICE_INCREASE_RATIO)
        stock.ask_price = get_comm_real_data(FID.ASK_PRICE)
        stock.bid_price = get_comm_real_data(FID.BID_PRICE)
        stock.volume = get_comm_real_data(FID.VOLUME)
        stock.accumulated_volume = get_comm_real_data(FID.ACCUMULATED_VOLUME)
        stock.highest_price = get_comm_real_data(FID.HIGHEST_PRICE)
        stock.lowest_price = get_comm_real_data(FID.LOWEST_PRICE)
        stock.opening_price = get_comm_real_data(FID.OPENING_PRICE)

        self.display_trading_table()

    def display_trading_table(self):
        for row, stock in enumerate(self.trading_items.values()):
            self.trading_table.setItem(row, 0, self.to_item(stock.item_name))
            self.trading_table.setItem(row, 1, self.to_item_time(stock.transaction_time))
            self.trading_table.setItem(row, 2, self.to_item(stock.current_price))
            self.trading_table.setItem(row, 3, self.to_item(stock.ask_price))
            self.trading_table.setItem(row, 4, self.to_item(stock.bid_price))
            self.trading_table.setItem(row, 5, self.to_item(stock.volume))
            self.trading_table.setItem(row, 6, self.to_item(stock.accumulated_volume))
            self.trading_table.setItem(row, 7, self.to_item(stock.highest_price))
            self.trading_table.setItem(row, 8, self.to_item(stock.lowest_price))
            self.trading_table.setItem(row, 9, self.to_item(stock.opening_price))

    def display_portfolio_table(self):
        for row, stock in enumerate(self.portfolio.values()):
            self.portfolio_table.setItem(row, 0, self.to_item(stock.item_name))
            self.portfolio_table.setItem(row, 1, self.to_item(stock.purchase_price))
            self.portfolio_table.setItem(row, 2, self.to_item(stock.profit))
            self.portfolio_table.setItem(row, 3, self.to_item(stock.profit_rate))
            self.portfolio_table.setItem(row, 4, self.to_item(stock.purchase_amount))
            self.portfolio_table.setItem(row, 5, self.to_item(stock.current_price))
            self.portfolio_table.setItem(row, 6, self.to_item(stock.purchase_sum))
            self.portfolio_table.setItem(row, 7, self.to_item(stock.evaluation_sum))
            self.portfolio_table.setItem(row, 8, self.to_item(stock.evaluation_fee))
            self.portfolio_table.setItem(row, 9, self.to_item(stock.tax))

    def obtain_order_info(self):
        item_code = self.get_chejan_data(FID.ITEM_CODE)
        order_number = self.get_chejan_data(FID.ORDER_NUMBER)
        order_state = self.get_chejan_data(FID.ORDER_STATE)
        order_amount = self.get_chejan_data(FID.ORDER_AMOUNT)
        order_price = self.get_chejan_data(FID.ORDER_PRICE)
        unconcluded_amount = self.get_chejan_data(FID.UNCONCLUDED_AMOUNT)
        original_order_number = self.get_chejan_data(FID.ORIGINAL_ORDER_NUMBER)
        order_type = self.get_chejan_data(FID.ORDER_TYPE)
        transaction_type = self.get_chejan_data(FID.TRANSACTION_TYPE)
        transaction_number = self.get_chejan_data(FID.TRANSACTION_NUMBER)
        transaction_price = self.get_chejan_data(FID.TRANSACTION_PRICE)
        transaction_amount = self.get_chejan_data(FID.TRANSACTION_AMOUNT)
        transaction_fee = self.get_chejan_data(FID.TRANSACTION_FEE)
        transaction_tax = self.get_chejan_data(FID.TRANSACTION_TAX)

        self.signal('order info')
        self.signal(item_code, order_number, order_state, order_amount, order_price, unconcluded_amount)
        self.signal(original_order_number, order_type)
        self.signal(transaction_type, transaction_number, transaction_price, transaction_amount, transaction_fee, transaction_tax)

    def obtain_balance_info(self):
        item_code = self.get_chejan_data(FID.ITEM_CODE)
        item_name = self.get_chejan_data(FID.ITEM_NAME)
        current_price = self.get_chejan_data(FID.CURRENT_PRICE)
        holding_amount = self.get_chejan_data(FID.HOLDING_AMOUNT)
        purchase_price = self.get_chejan_data(FID.PURCHASE_PRICE)
        purchase_sum = self.get_chejan_data(FID.PURCHASE_SUM)
        purchase_today = self.get_chejan_data(FID.PURCHASE_TODAY)
        buy_or_sell = self.get_chejan_data(FID.BUY_OR_SELL)
        sell_today = self.get_chejan_data(FID.SELL_TODAY)
        reference_price = self.get_chejan_data(FID.REFERENCE_PRICE)
        profit_rate = self.get_chejan_data(FID.PROFIT_RATE)
        profit_realization = self.get_chejan_data(FID.PROFIT_REALIZATION)
        profit_realization_rate = self.get_chejan_data(FID.PROFIT_REALIZATION_RATE)

        self.signal('balance info')
        self.signal(item_code, item_name, current_price, holding_amount, purchase_price, purchase_sum)
        self.signal(purchase_today, buy_or_sell, sell_today, reference_price, profit_rate)
        self.signal(profit_realization, profit_realization_rate)

    def execute_algorithm(self):
        self.signal('running algorithm')
        send_order = self.new_send_order('order', self.screen_send_order, self.account_number, 1)
        send_order('122630', 1, 19000, '00', '')

    def init_screen(self, sScrNo):
        self.dynamic_call('DisconnectRealData', sScrNo)
        self.debug('Screen disconnected', sScrNo)

    def on_receive_condition_ver(self, IRet, sMsg):
        self.debug('receive condition ver', IRet, sMsg)

    def close_process(self):
        self.dynamic_call('SetRealRemove', 'ALL', 'ALL')
        self.signal('All screens are disconnected')