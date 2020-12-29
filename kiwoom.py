from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import QObject, QThread
import pandas
from datetime import datetime
import time
from kiwoombase import KiwoomBase
from wookauto import LoginPasswordThread, AccountPasswordThread
from wookstock import Stock
from wookdata import *

class Kiwoom(KiwoomBase):
    def __init__(self, log, key):
        super().__init__(log, key)
        self.info('Kiwoom initializing...')

        # Connect slots
        self.OnEventConnect.connect(self.on_login)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveRealData.connect(self.on_receive_real_data)
        self.OnReceiveChejanData.connect(self.on_receive_chejan_data)
        self.OnReceiveMsg.connect(self.on_receive_msg)
        self.OnReceiveConditionVer.connect(self.on_receive_condition_ver)

        self.demand_market_state_info()

        self.count = 0

        # self.portfolio_request_complete = True

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
            self.log('Failed to get account information')
        else:
            self.log('Account information')
        return self.account_list

    def request_deposit_info(self, sPrevNext='0'):
        self.check_request_time()
        self.set_input_value(ACCOUNT_NUMBER, self.account_number)
        self.set_input_value(PASSWORD, self.account_password)
        self.set_input_value(PASSWORD_MEDIA_TYPE, '00')
        self.set_input_value(INQUIRY_TYPE, '1')
        self.comm_rq_data('deposit', REQUEST_DEPOSIT_INFO, sPrevNext, self.screen_account)

    def request_portfolio_info(self, sPrevNext='0'):
        self.check_request_time()
        self.set_input_value(ACCOUNT_NUMBER, self.account_number)
        self.set_input_value(PASSWORD, self.account_password)
        self.set_input_value(PASSWORD_MEDIA_TYPE, '00')
        self.set_input_value(INQUIRY_TYPE, '1')
        self.comm_rq_data('portfolio', REQUEST_PORTFOLIO_INFO, sPrevNext, self.screen_portfolio)

    def request_order_history(self, item_code='', sPrevNext='0'):
        self.check_request_time()
        self.set_input_value(ACCOUNT_NUMBER, self.account_number)
        self.set_input_value(ALL_OR_INDIVIDUAL, ALL)
        self.set_input_value(TRADE_POSITION, POSITION.ALL)
        self.set_input_value(ITEM_CODE, item_code)
        self.set_input_value(ORDER_EXECUTION_TYPE, ORDER.ALL)
        self.comm_rq_data('order history', REQUEST_OPEN_ORDER, sPrevNext, self.screen_open_order)

    def request_stock_price_min(self, item_code, sPrevNext='0'):
        self.check_request_time()
        self.set_input_value(ITEM_CODE, item_code)
        self.set_input_value(TICK_RANGE, MIN_1)
        self.set_input_value(CORRECTED_PRICE_TYPE, '1')
        self.comm_rq_data('stock price min', REQUEST_MINUTE_PRICE, sPrevNext, self.screen_stock_price)

    def demand_market_state_info(self):
        self.set_real_reg(self.screen_operation_state, ' ', FID.MARKET_OPERATION_STATE, '0')

    def demand_trading_item_info(self, item_code):
        self.set_real_reg(item_code, item_code, FID.TRANSACTION_TIME, '1')

    def order(self, item_code, price, amount, order_position_text, order_type, order_number):
        self.order_position = order_position_text
        order_position = ORDER_POSITION_DICT[order_position_text]
        send_order = self.new_send_order('order', self.screen_send_order, self.account_number)
        send_order(order_position, item_code, amount, price, order_type, order_number)

    def on_login(self, err_code):
        if err_code == 0:
            self.log('Kiwoom log in success')
        else:
            self.log('Something is wrong during log-in')
            self.error('Login error', err_code)

        self.login_event_loop.exit()

    def on_receive_msg(self, sScrNo, sRQName, sTrCode, sMsg):
        self.inquiry_count += 1
        time = datetime.now().strftime('%H:%M:%S')
        self.status(sMsg, sRQName, time, '('+str(self.inquiry_count)+')')

    def on_receive_tr_data(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        # self.debug('tr_data', sScrNo, sRQName, sTrCode)
        if sRQName == 'deposit':
            self.get_deposit_info(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'portfolio':
            self.get_portfolio_info(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'order':
            self.get_order_state(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'order history':
            self.get_order_history(sTrCode, sRecordName, sScrNo, sPrevNext)
        elif sRQName == 'stock price min':
            self.get_stock_price_min(sTrCode, sRecordName, sScrNo, sPrevNext)

    def on_receive_real_data(self, sCode, sRealType, sRealData):
        # self.debug('real_data', sCode, sRealType, sRealData)
        if sRealType == REAL_TYPE_MARKET_OPENING_TIME:
            self.update_market_state(sCode)
        elif sRealType == REAL_TYPE_STOCK_TRADED:
            self.update_trading_items(sCode)
        elif sRealType == REAL_TYPE_FUTURES_TRADED:
            self.update_futures_trading_items(sCode)

    def on_receive_chejan_data(self, sGubun, nItemCnt, nFidList):
        # self.debug('chejan', sGubun, nItemCnt, nFidList)
        if sGubun == CHEJAN_EXECUTED_ORDER:
            self.obtain_executed_order_info()
        elif sGubun == CHEJAN_BALANCE:
            self.obtain_balance_info()

    def get_deposit_info(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        get_comm_data = self.new_get_comm_data(sTrCode, sRecordName, 0)
        self.deposit = get_comm_data(DEPOSIT)
        self.withdrawable = get_comm_data(WITHDRAWABLE)
        self.orderable_money = get_comm_data(ORDERABLE)

        self.signal('deposit')
        self.info('Deposit information')
        self.init_screen(sScrNo)
        self.deposit_requester.quit()

    def get_portfolio_info(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        number_of_item = self.get_repeat_count(sTrCode, sRecordName)
        for count in range(number_of_item):
            get_comm_data = self.new_get_comm_data(sTrCode, sRecordName, count)

            stock = Stock()
            stock.item_code = get_comm_data(ITEM_NUMBER)[1:]
            stock.item_name = get_comm_data(ITEM_NAME)
            stock.current_price = get_comm_data(CURRENT_PRICE)
            stock.purchase_price = get_comm_data(PURCHASE_PRICE)
            stock.holding_amount = get_comm_data(HOLDING_AMOUNT)
            stock.purchase_sum = get_comm_data(PURCHASE_SUM)
            stock.evaluation_sum = get_comm_data(EVALUATION_SUM)
            stock.total_fee = get_comm_data(TOTAL_FEE)
            stock.tax = get_comm_data(TAX)
            stock.profit = get_comm_data(PROFIT)
            stock.profit_rate = get_comm_data(PROFIT_RATE)

            self.portfolio[stock.item_code] = stock

        if sPrevNext == '2':
            self.request_portfolio_info(sPrevNext)
        else:
            self.signal('portfolio')
            self.signal('portfolio_table')
            self.info('Portfolio information')
            self.init_screen(sScrNo)
            self.portfolio_requester.quit()

    def get_order_history(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        self.order_history.clear()
        number_of_order = self.get_repeat_count(sTrCode, sRecordName)
        for count in range(number_of_order):
            get_comm_data = self.new_get_comm_data(sTrCode, sRecordName, count)

            stock = Stock()
            stock.item_code = get_comm_data(ITEM_CODE)
            stock.item_name = get_comm_data(ITEM_NAME)
            stock.order_executed_time = get_comm_data(TIME)
            stock.order_amount = get_comm_data(ORDER_AMOUNT)
            stock.executed_amount = get_comm_data(EXECUTED_ORDER_AMOUNT)
            stock.open_amount = get_comm_data(OPEN_AMOUNT)
            stock.order_number = get_comm_data(ORDER_NUMBER)
            stock.original_order_number = get_comm_data(ORIGINAL_ORDER_NUMBER)
            stock.order_price = get_comm_data(ORDER_PRICE)
            stock.executed_price = get_comm_data(EXECUTED_ORDER_PRICE)
            stock.order_position = get_comm_data(ORDER_POSITION)
            stock.order_state = get_comm_data(ORDER_STATE)
            # stock.trade_position = get_comm_data(TRADE_POSITION)
            # stock.executed_order_number = get_comm_data(EXECUTED_ORDER_NUMBER)

            self.order_history[stock.order_number] = stock
            if stock.open_amount != 0:
                self.open_orders[stock.order_number] = stock

        if sPrevNext == '2':
            self.request_order_history(sPrevNext)
        else:
            self.signal('order_history_table')
            self.signal('open_orders_table')
            self.info('Order history information')
            self.init_screen(sScrNo)
            self.order_history_requester.quit()

    def get_stock_price_min(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        number_of_item = self.get_repeat_count(sTrCode, sRecordName)
        today = int(datetime.today().strftime('%Y%m%d'))
        item_code = self.get_comm_data(sTrCode, sRecordName, 0, ITEM_CODE)
        self.stock_prices.clear()

        for count in range(number_of_item):
            get_comm_data = self.new_get_comm_data(sTrCode, sRecordName, count)
            transaction_time = str(get_comm_data(TRANSACTION_TIME))
            current_date = int(transaction_time[:8])

            if current_date < today:
                self.stock_prices.reverse()
                self.signal('chart')
                self.init_screen(sScrNo)
                return

            open_price = int(abs(get_comm_data(OPEN_PRICE)))
            high_price = int(abs(get_comm_data(HIGH_PRICE)))
            low_price = int(abs(get_comm_data(LOW_PRICE)))
            current_price = int(abs(get_comm_data(CURRENT_PRICE)))
            volume = int(abs(get_comm_data(VOLUME)))

            data = [transaction_time, open_price, high_price, low_price, current_price, volume]
            self.stock_prices.append(data)

        if sPrevNext == '2':
            self.request_stock_price_min(item_code, sPrevNext)

    def get_order_state(self, sTrCode, sRecordName, sScrNo, sPrevNext):
        get_comm_data = self.new_get_comm_data(sTrCode, sRecordName)
        order_number = get_comm_data(0, ORDER_NUMBER)
        if order_number:
            self.debug('Send order ({}) command committed successfully'.format(self.order_position), sTrCode)
        else:
            self.debug('Send order failed.', 'Please check order variables')

    def update_market_state(self, sCode):
        operation_state = self.get_comm_real_data(sCode, FID.MARKET_OPERATION_STATE)
        present_time = self.get_comm_real_data(sCode, FID.TRANSACTION_TIME, time=True)
        remaining_time = self.get_comm_real_data(sCode, FID.MARKET_OPERATION_REMAINING_TIME, time=True)
        self.info('market operation state', operation_state, present_time, remaining_time)

    def update_trading_items(self, item_code):
        stock = self.trading_items[item_code]
        get_comm_real_data = self.new_get_comm_real_data(item_code)

        stock.transaction_time = get_comm_real_data(FID.TRANSACTION_TIME)
        stock.current_price = get_comm_real_data(FID.CURRENT_PRICE)
        stock.price_increase_amount = get_comm_real_data(FID.PRICE_INCREASE_AMOUNT)
        stock.ask_price = get_comm_real_data(FID.ASK_PRICE)
        stock.bid_price = get_comm_real_data(FID.BID_PRICE)
        stock.volume = get_comm_real_data(FID.VOLUME)
        stock.accumulated_volume = get_comm_real_data(FID.ACCUMULATED_VOLUME)
        stock.high_price = get_comm_real_data(FID.HIGH_PRICE)
        stock.low_price = get_comm_real_data(FID.LOW_PRICE)
        stock.open_price = get_comm_real_data(FID.OPEN_PRICE)
        # stock.price_increase_ratio = get_comm_real_data(FID.PRICE_INCREASE_RATIO)

        self.signal('trading_items_table')

        if stock.current_price < 0:
            stock.current_price = stock.current_price * -1

        time = datetime.now().strftime('%Y%m%d%H%M')
        price = stock.current_price
        if self.stock_prices == []:
            self.request_stock_price_min(item_code)
            # self.stock_prices = [['202012291305', 22000, 22000, 22000, 22000, 22000]]
            self.timer.start()
            return
        elif time != self.stock_prices[-1][0]:
            price_data = [time, price, price, price, price, stock.volume]
            self.stock_prices.append(price_data)
        else:
            if price > self.stock_prices[-1][2]:
                self.stock_prices[-1][2] = price
            elif price < self.stock_prices[-1][3]:
                self.stock_prices[-1][3] = price
            self.stock_prices[-1][4] = price
            self.stock_prices[-1][5] += stock.volume
        self.signal('chart')

        self.count += 1
        print(self.count)

        if item_code in self.portfolio:
            self.update_portfolio(item_code, stock.current_price)

    def update_futures_trading_items(self, item_code):
        stock = self.trading_items[item_code]
        get_comm_real_data = self.new_get_comm_real_data(item_code)

        stock.transaction_time = get_comm_real_data(FID.TRANSACTION_TIME)
        stock.current_price = get_comm_real_data(FID.CURRENT_PRICE)
        stock.price_increase_amount = get_comm_real_data(FID.PRICE_INCREASE_AMOUNT)
        stock.ask_price = get_comm_real_data(FID.ASK_PRICE)
        stock.bid_price = get_comm_real_data(FID.BID_PRICE)
        stock.volume = get_comm_real_data(FID.VOLUME)
        stock.accumulated_volume = get_comm_real_data(FID.ACCUMULATED_VOLUME)
        stock.high_price = get_comm_real_data(FID.HIGH_PRICE)
        stock.low_price = get_comm_real_data(FID.LOW_PRICE)
        stock.open_price = get_comm_real_data(FID.OPEN_PRICE)
        # stock.price_increase_ratio = get_comm_real_data(FID.PRICE_INCREASE_RATIO)

        self.signal('trading_items_table')

        if stock.current_price < 0:
            stock.current_price = stock.current_price * -1

        if item_code in self.portfolio:
            self.update_portfolio(item_code, stock.current_price)

    def obtain_executed_order_info(self):
        stock = Stock()
        stock.item_code = self.get_chejan_data(FID.ITEM_CODE)[1:]
        stock.item_name = self.get_item_name(stock.item_code)
        stock.order_executed_time = self.get_chejan_data(FID.ORDER_EXECUTED_TIME)
        stock.order_amount = self.get_chejan_data(FID.ORDER_AMOUNT)
        stock.executed_amount = self.get_chejan_data(FID.EXECUTED_AMOUNT, number=True)
        stock.open_amount = self.get_chejan_data(FID.OPEN_AMOUNT)
        stock.order_number = self.get_chejan_data(FID.ORDER_NUMBER)
        stock.original_order_number = self.get_chejan_data(FID.ORIGINAL_ORDER_NUMBER)
        stock.executed_order_number = self.get_chejan_data(FID.EXECUTED_ORDER_NUMBER)
        stock.order_price = self.get_chejan_data(FID.ORDER_PRICE)
        stock.executed_price = self.get_chejan_data(FID.EXECUTED_PRICE)
        stock.order_position = self.get_chejan_data(FID.ORDER_POSITION)
        stock.current_price = self.get_chejan_data(FID.CURRENT_PRICE)

        stock.order_state = self.get_chejan_data(FID.ORDER_STATE)
        stock.order_type = self.get_chejan_data(FID.ORDER_POSITION)
        stock.transaction_type = self.get_chejan_data(FID.TRANSACTION_TYPE)
        stock.transaction_price = self.get_chejan_data(FID.EXECUTED_PRICE)
        stock.volume = self.get_chejan_data(FID.VOLUME)
        stock.transaction_fee = self.get_chejan_data(FID.TRANSACTION_FEE)
        stock.tax = self.get_chejan_data(FID.TRANSACTION_TAX)

        if self.algorithm_manager.hold(stock):
            self.algorithm_manager.add_stock(stock)
            self.signal('algorithm_trading_table')

        self.open_orders[stock.order_number] = stock
        if (stock.order_number in self.open_orders) and (stock.open_amount == 0):
            del self.open_orders[stock.order_number]
        self.signal('open_orders_table')
        self.order_history_requester.start()

        message = 'Order execution {}({}), '.format(stock.item_name, stock.order_state)
        message += 'order:{}, executed:{}, '.format(stock.order_amount, stock.executed_amount)
        message += 'order number:{}, original number:{}'.format(stock.order_number, stock.original_order_number)
        self.log(message)

    def obtain_balance_info(self):
        stock = Stock()
        stock.item_code = self.get_chejan_data(FID.ITEM_CODE)[1:]
        stock.item_name = self.get_chejan_data(FID.ITEM_NAME)
        stock.current_price = self.get_chejan_data(FID.CURRENT_PRICE)
        stock.reference_price = self.get_chejan_data(FID.REFERENCE_PRICE)
        stock.purchase_price_avg = self.get_chejan_data(FID.PURCHASE_PRICE_AVG)
        stock.holding_amount = self.get_chejan_data(FID.HOLDING_AMOUNT)
        stock.purchase_amount_net_today = self.get_chejan_data(FID.PURCHASE_AMOUNT_NET_TODAY)
        stock.purchase_sum = self.get_chejan_data(FID.PURCHASE_SUM)
        Stock.balance_profit_net_today = self.get_chejan_data(FID.PROFIT_NET_TODAY)
        Stock.balance_profit_rate = self.get_chejan_data(FID.PROFIT_RATE)
        Stock.balance_profit_realization = self.get_chejan_data(FID.PROFIT_REALIZATION)
        # Stock.balance_profit_realization_rate = self.get_chejan_data(FID.PROFIT_REALIZATION_RATE)
        # stock.buy_or_sell = self.get_chejan_data(FID.BUY_OR_SELL)
        # stock.deposit = self.get_chejan_data(FID.DEPOSIT)

        self.balance[stock.item_code] = stock
        self.signal('balance_table')
        self.info('Balance information')

        self.request_deposit_info()
        self.request_portfolio_info()
        # self.deposit_requester.start()
        # self.portfolio_requester.start()

    def execute_algorithm(self):
        self.log('Running algorithm started')

        stock = Stock()
        stock.item_code = '122630'
        stock.order_price = 21400
        stock.order_amount = 100
        stock.trade_position = 'BUY'
        stock.order_type = ORDER_TYPE['LIMIT']

        order_parameters = [stock.item_code, stock.order_price, stock.order_amount]
        order_parameters += [stock.trade_position, stock.order_type, stock.order_number]
        self.algorithm_manager.add_stock(stock)

        self.order(*order_parameters)

    def update_portfolio(self, item_code, current_price):
        stock = self.portfolio[item_code]
        evaluation_sum = stock.holding_amount * current_price
        evaluation_fee = int(evaluation_sum * 0.00035) * 10
        purchase_sum = stock.purchase_price * stock.holding_amount
        purchase_fee = round(int(purchase_sum * 0.00035 * 10), -1)
        total_fee = evaluation_fee + purchase_fee
        tax = int(evaluation_sum * 0.0025)
        profit = evaluation_sum - purchase_sum - total_fee - tax
        profit_rate = round((profit / purchase_sum) * 100, 2)

        stock.current_price = current_price
        stock.evaluation_sum = evaluation_sum
        stock.profit = profit
        stock.profit_rate = profit_rate
        stock.total_fee = total_fee
        stock.tax = tax

        self.signal('portfolio_table')

    def on_every_min(self):
        self.debug('Timer worked')
        time = datetime.now().strftime('%Y%m%d%H%M')
        if self.stock_prices == []:
            return
        if time != self.stock_prices[-1][0]:
            price = self.stock_prices[-1][4]
            data = [time, price, price, price, price, 0]
            self.stock_prices.append(data)
        self.signal('chart')

    def check_request_time(self):
        current_time = time.time()
        interval = current_time - self.request_time
        waiting_time = self.request_interval_limit - interval
        # self.debug('===== Request time check =====', interval)
        if interval < self.request_interval_limit:
            # self.debug('===== Waiting for time interval ===== ', waiting_time)
            time.sleep(waiting_time)
        self.request_time = time.time()

    def init_screen(self, sScrNo):
        self.dynamic_call('DisconnectRealData', sScrNo)
        # self.debug('Screen reset', sScrNo)

    def on_receive_condition_ver(self, IRet, sMsg):
        self.debug('receive condition ver', IRet, sMsg)

    def close_process(self):
        self.dynamic_call('SetRealRemove', 'ALL', 'ALL')
        self.log('All screens are disconnected')