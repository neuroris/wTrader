from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog
from PyQt5.QtCore import Qt
from datetime import datetime
from traderbase import TraderBase
from kiwoom import Kiwoom
from wookstock import Stock
from wookdata import *

class Trader(TraderBase):
    def __init__(self, log, key):
        self.kiwoom = Kiwoom(log, key)
        super().__init__(log)
        self.initKiwoom()

        # Initial work
        self.connect_kiwoom()
        self.get_account_list()
        self.get_deposit_info()
        self.get_portfolio_info()

        # auto add
        # self.btn_add_item.click()
        # self.cbb_item_code.setCurrentIndex(1)
        # self.btn_add_item.click()

    def test(self):
        item_code = self.cbb_item_code.currentText()
        self.kiwoom.request_concluded_order_info(item_code)

    def initKiwoom(self):
        self.kiwoom.signal = self.on_kiwoom_signal
        self.kiwoom.signal_portfolio_table = self.display_portfolio_table
        self.kiwoom.signal_trading_table = self.display_trading_table
        self.kiwoom.status = self.on_kiwoom_status

    def connect_kiwoom(self):
        if self.cb_auto_login.isChecked():
            self.kiwoom.auto_login()
        else:
            self.kiwoom.login()
            self.kiwoom.set_account_password()

    def get_account_list(self):
        account_list = self.kiwoom.get_account_list()
        if account_list is not None:
            self.cbb_account.addItems(self.kiwoom.account_list)

    def get_deposit_info(self):
        self.kiwoom.request_deposit_info()
        self.lb_deposit.setText(self.kiwoom.deposit)

    def get_portfolio_info(self):
        self.kiwoom.request_portfolio_info()

    def display_trading_table(self, trading_items):
        for row, stock in enumerate(trading_items.values()):
            self.table_trading.setItem(row, 0, self.to_item(stock.item_name))
            self.table_trading.setItem(row, 1, self.to_item_time(stock.transaction_time))
            self.table_trading.setItem(row, 2, self.to_item(stock.current_price))
            self.table_trading.setItem(row, 3, self.to_item(stock.ask_price))
            self.table_trading.setItem(row, 4, self.to_item(stock.bid_price))
            self.table_trading.setItem(row, 5, self.to_item(stock.volume))
            self.table_trading.setItem(row, 6, self.to_item(stock.accumulated_volume))
            self.table_trading.setItem(row, 7, self.to_item(stock.highest_price))
            self.table_trading.setItem(row, 8, self.to_item(stock.lowest_price))
            self.table_trading.setItem(row, 9, self.to_item(stock.opening_price))

    def display_portfolio_table(self, portfolio):
        for row, stock in enumerate(portfolio.values()):
            self.table_portfolio.setItem(row, 0, self.to_item(stock.item_name))
            self.table_portfolio.setItem(row, 1, self.to_item(stock.purchase_price))
            self.table_portfolio.setItem(row, 2, self.to_item(stock.profit))
            self.table_portfolio.setItem(row, 3, self.to_item(stock.profit_rate))
            self.table_portfolio.setItem(row, 4, self.to_item(stock.purchase_amount))
            self.table_portfolio.setItem(row, 5, self.to_item(stock.current_price))
            self.table_portfolio.setItem(row, 6, self.to_item(stock.purchase_sum))
            self.table_portfolio.setItem(row, 7, self.to_item(stock.evaluation_sum))
            self.table_portfolio.setItem(row, 8, self.to_item(stock.evaluation_fee))
            self.table_portfolio.setItem(row, 9, self.to_item(stock.tax))

    def go(self):
        self.kiwoom.execute_algorithm()

    def on_select_account(self, account):
        self.kiwoom.account_number = int(account)

    def on_select_item_code(self, code):
        item_name = self.get_item_name(code)
        self.cbb_item_name.setCurrentText(item_name)

    def on_select_item_name(self, name):
        item_code = self.get_item_code(name)
        self.cbb_item_code.setCurrentText(item_code)

    def on_add_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code in self.kiwoom.trading_items:
            return

        stock = Stock()
        stock.item_code = item_code
        stock.item_name = item_name
        self.kiwoom.trading_items[item_code] = stock
        self.kiwoom.demand_trading_item_info(item_code)
        self.kiwoom.signal(stock.item_name, 'stock information begins to be monitored')

    def on_remove_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code not in self.kiwoom.trading_items:
            return

        self.kiwoom.init_screen(item_code)
        del self.kiwoom.trading_items[item_code]
        self.table_trading.clearContents()
        self.display_trading_table(self.kiwoom.trading_items)
        self.kiwoom.signal(item_name, 'stock information monitoring is finished')

    def on_edit_save_file(self):
        file = self.le_save_file.text()
        self.kiwoom.log_file = file

    def on_change_save_file(self):
        file = QFileDialog.getOpenFileName(self, 'Select File', self.setting['save_folder'])[0]
        if file != '':
            self.le_save_file.setText(file)
            self.kiwoom.log_file = file

    def edit_setting(self):
        self.debug('setting')

    def get_item_name(self, code):
        item_name = ''
        if code == CODE_KODEX_LEVERAGE:
            item_name = NAME_KODEX_LEVERAGE
        elif code == CODE_KODEX_INVERSE_2X:
            item_name = NAME_KODEX_INVERSE_2X

        return item_name

    def get_item_code(self, name):
        item_code = ''
        if name == NAME_KODEX_LEVERAGE:
            item_code = CODE_KODEX_LEVERAGE
        elif name == NAME_KODEX_INVERSE_2X:
            item_code = CODE_KODEX_INVERSE_2X

        return item_code

    def on_kiwoom_signal(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        time = datetime.now().strftime('%H:%M:%S') + ' '
        self.te_info.append(time + message)
        self.info(message)

    def on_kiwoom_status(self, *args):
        message = str(args[0])
        for arg in args[1:]:
            message += ' ' + str(arg)
        self.status_bar.showMessage(message)

    def closeEvent(self, event):
        self.kiwoom.signal('Closing process initializing...')
        self.kiwoom.close_process()
        self.kiwoom.clear()
        self.kiwoom.deleteLater()
        self.deleteLater()