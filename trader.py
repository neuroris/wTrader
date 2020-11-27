from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog
from traderbase import TraderBase
from kiwoom import Kiwoom
from wookstock import Stock
from wookdata import *
from datetime import datetime

class Trader(TraderBase):
    def __init__(self, log, key):
        self.kiwoom = Kiwoom(log, key)
        super().__init__(log)
        self.initKiwoom()

        # Initial work
        self.connect_kiwoom()
        self.get_account_list()
        self.get_deposit_info()
        # self.get_portfolio_info()

        # auto add
        # self.btn_add_item.click()
        # self.cbb_item_code.setCurrentIndex(1)
        # self.btn_add_item.click()

    def test(self):
        name = self.kiwoom.get_item_name(self.cbb_item_code.currentText())
        self.debug(name)

    def initKiwoom(self):
        self.kiwoom.signal = self.on_kiwoom_signal
        self.kiwoom.status = self.on_kiwoom_status
        self.kiwoom.portfolio_table = self.table_portfolio
        self.kiwoom.trading_table = self.table_trading
        # self.kiwoom.save_file = self.le_save_file.text()

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
        self.kiwoom.signal(stock.item_name, ' stock information begins to be monitored')

    def on_remove_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code not in self.kiwoom.trading_items:
            return

        self.kiwoom.init_screen(item_code)
        del self.kiwoom.trading_items[item_code]
        self.table_trading.clearContents()
        self.kiwoom.display_trading_table()
        self.kiwoom.signal(item_name, ' stock information monitoring is finished')

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