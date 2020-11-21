from traderbase import TraderBase

class Trader(TraderBase):
    def __init__(self, log, key):
        super().__init__(log, key)

        # Auto login
        self.on_connect_kiwoom()

    def test(self):
        self.debug('test button clicked')

    def on_connect_kiwoom(self):
        login_status = self.kiwoom.connect(self.cb_auto_login.isChecked())
        if login_status != 0:
            self.status_bar.showMessage('Something is wrong during log-in')
            self.error('Login error', login_status)
            return

        self.status_bar.showMessage('Log in success')
        self.cbb_account.addItems(self.kiwoom.account_list)

    def get_stock_price(self):
        self.info('Getting stock price...')
        if self.rb_tick.isChecked():
            self.status_bar.showMessage('Getting stock prices (tick data)...')
            self.kiwoom.request_stock_price_tick()
        elif self.rb_min.isChecked():
            self.status_bar.showMessage('Getting stock prices (minute data)...')
            self.kiwoom.request_stock_price_min()
        elif self.rb_day.isChecked():
            self.status_bar.showMessage('Getting stock prices (day data)...')
            self.kiwoom.request_stock_price_day()

    def get_item_info(self):
        pass

    def closeEvent(self, event):
        self.info('Closing process initializing...')
        self.kiwoom.clear()
        self.kiwoom.deleteLater()
        self.deleteLater()