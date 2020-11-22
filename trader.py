from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog
from traderbase import TraderBase
from kiwoom import Kiwoom
from wookstock import Stock
from wookdata import *

class Trader(TraderBase):
    def __init__(self, log, key):
        self.kiwoom = Kiwoom(log, key)
        super().__init__(log, key)
        self.initKiwoom()

        # Auto login
        self.on_connect_kiwoom()

        # auto add
        # self.btn_add_item.click()
        # self.cbb_item_code.setCurrentIndex(1)
        # self.btn_add_item.click()



    def test(self):
        self.debug('test button clicked')
        self.kiwoom.update_interesting_items('122630')

    def initKiwoom(self):
        self.kiwoom.signal = self.on_kiwoom_signal
        self.kiwoom.signal_market_status = self.on_kiwoom_market_status
        self.kiwoom.signal_trading_item = self.on_kiwoom_trading_item
        self.kiwoom.portpolio_table = self.portfolio_table
        self.kiwoom.trading_table = self.trading_table
        self.kiwoom.status = self.on_kiwoom_status
        self.kiwoom.item_code = self.cbb_item_code.currentText()
        self.kiwoom.item_name = self.cbb_item_name.currentText()
        self.kiwoom.save_file = self.le_save_file.text()

    def on_connect_kiwoom(self):
        login_status = self.kiwoom.connect(self.cb_auto_login.isChecked())
        if login_status != 0:
            self.status_bar.showMessage('Something is wrong during log-in')
            self.error('Login error', login_status)
            return

        self.status_bar.showMessage('Log in success')
        self.cbb_account.addItems(self.kiwoom.account_list)

    def get_item_info(self):
        self.kiwoom.demand_item_info()

    def on_kiwoom_signal(self, *args):
        message = ''
        for arg in args:
            message += str(arg) + ' '

        self.te_info.append(message)

    def on_kiwoom_market_status(self, operation_state):
        if operation_state == '0':
            self.info('it is before market opening!')
            self.lb_market_status.setText('before open')
        elif operation_state == '3':
            self.info('it is market opening hours')
            self.lb_market_status.setText('opening hour')
        elif operation_state == '2':
            self.info('market is closed')
            self.lb_market_status.setText('closed')
        elif operation_state == '4':
            self.info('single price market is over')
            self.lb_market_status.setText('single over')

    def on_kiwoom_trading_item(self):
        pass

    def on_kiwoom_status(self, message):
        self.status_bar.showMessage(message)

    def on_select_account(self, account):
        self.kiwoom.account_number = int(account)

    def on_select_item_code(self, code):
        self.kiwoom.item_code = int(code)
        item_name = self.get_item_name(code)
        self.cbb_item_name.setCurrentText(item_name)

    def on_select_item_name(self, name):
        self.kiwoom.item_name = name
        item_code = self.get_item_code(name)
        self.cbb_item_code.setCurrentText(item_code)

    def on_add_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()

        stock = Stock()
        stock.item_name = item_name
        self.kiwoom.trading_items[item_code] = stock
        self.kiwoom.demand_trading_item_info(item_code)

    def on_remove_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code not in self.kiwoom.trading_item_list:
            return
        self.kiwoom.trading_item_list.remove(item_code)
        self.kiwoom.trading_item_list.sort()
        self.trading_table.clearContents()

        for index in range(len(self.kiwoom.trading_item_list)):
            self.trading_table.setItem(index, 0, QTableWidgetItem(self.kiwoom.trading_item_list[index]))

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

    def closeEvent(self, event):
        self.info('Closing process initializing...')
        self.kiwoom.clear()
        self.kiwoom.deleteLater()
        self.deleteLater()