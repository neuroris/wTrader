from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog, QTableWidgetSelectionRange
from PyQt5.QtCore import Qt, QThread
from datetime import datetime
from traderbase import TraderBase
from kiwoom import Kiwoom
from wookstock import Stock
from wookdata import *
import time

class Trader(TraderBase):
    def __init__(self, log, key):
        self.kiwoom = Kiwoom(log, key)
        super().__init__(log)
        self.initKiwoom()

        # Initial work
        self.connect_kiwoom()
        self.get_account_list()
        self.kiwoom.request_deposit_info()
        self.kiwoom.request_portfolio_info()

        # For debugging convenience
        self.cbb_item_code.setCurrentIndex(2)

    def test(self):
        self.debug('test button clicked')

        self.kiwoom.request_args = '048260'
        self.kiwoom.request = 'order_history'
        self.kiwoom.order_history_requester.start()

    def go(self):
        self.kiwoom.order_history_requester.start()
        pass

    def initKiwoom(self):
        self.kiwoom.log = self.on_kiwoom_log
        self.kiwoom.signal = self.on_kiwoom_signal
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

    def update_deposit_info(self):
        deposit = '\\' + self.formalize(self.kiwoom.deposit)
        orderable_money = '\\' + self.formalize(self.kiwoom.orderable_money)
        self.lb_deposit.setText(deposit)
        self.lb_orderable.setText(orderable_money)

    def update_order_variables(self):
        if not self.kiwoom.account_number:
            return

        stock = Stock()
        item_code = self.cbb_item_code.currentText()
        if item_code in self.kiwoom.portfolio:
            stock = self.kiwoom.portfolio[item_code]

        buyable_amount = 'no info'
        if stock.current_price != 0:
            buyable_amount = self.formalize(self.kiwoom.orderable_money // stock.current_price)
        self.lb_buyable.setText(buyable_amount)
        self.lb_sellable.setText(self.formalize(stock.holding_amount))
        self.sb_price.setValue(stock.current_price)

    def display_portfolio(self):
        self.clear_table(self.table_portfolio)

        for row, stock in enumerate(self.kiwoom.portfolio.values()):
            self.table_portfolio.insertRow(row)
            self.table_portfolio.setRowHeight(row, 8)
            self.table_portfolio.setItem(row, 0, self.to_item(stock.item_name))
            self.table_portfolio.setItem(row, 1, self.to_item(stock.current_price))
            self.table_portfolio.setItem(row, 2, self.to_item(stock.purchase_price))
            self.table_portfolio.setItem(row, 3, self.to_item(stock.holding_amount))
            self.table_portfolio.setItem(row, 4, self.to_item(stock.purchase_sum))
            self.table_portfolio.setItem(row, 5, self.to_item(stock.evaluation_sum))
            self.table_portfolio.setItem(row, 6, self.to_item_sign(stock.profit))
            self.table_portfolio.setItem(row, 7, self.to_item_sign(stock.profit_rate))
            self.table_portfolio.setItem(row, 8, self.to_item(stock.evaluation_fee))
            self.table_portfolio.setItem(row, 9, self.to_item(stock.tax))
        self.table_portfolio.sortItems(0, Qt.DescendingOrder)

    def display_trading_items(self):
        for row, stock in enumerate(self.kiwoom.trading_items.values()):
            self.table_trading_items.setItem(row, 0, self.to_item(stock.item_name))
            self.table_trading_items.setItem(row, 1, self.to_item_time(stock.transaction_time))
            self.table_trading_items.setItem(row, 2, self.to_item(stock.current_price))
            self.table_trading_items.setItem(row, 3, self.to_item(stock.ask_price))
            self.table_trading_items.setItem(row, 4, self.to_item(stock.bid_price))
            self.table_trading_items.setItem(row, 5, self.to_item(stock.volume))
            self.table_trading_items.setItem(row, 6, self.to_item(stock.accumulated_volume))
            self.table_trading_items.setItem(row, 7, self.to_item(stock.high_price))
            self.table_trading_items.setItem(row, 8, self.to_item(stock.low_price))
            self.table_trading_items.setItem(row, 9, self.to_item(stock.open_price))
        self.table_trading_items.sortItems(0, Qt.DescendingOrder)

    def display_open_orders(self):
        self.clear_table(self.table_open_orders)
        for row, stock in enumerate(self.kiwoom.open_orders.values()):
            self.table_open_orders.insertRow(row)
            self.table_open_orders.setRowHeight(row, 8)
            self.table_open_orders.setItem(row, 0, self.to_item(stock.item_name))
            self.table_open_orders.setItem(row, 1, self.to_item_time(stock.order_executed_time))
            self.table_open_orders.setItem(row, 2, self.to_item(stock.order_amount))
            self.table_open_orders.setItem(row, 3, self.to_item(stock.executed_amount))
            self.table_open_orders.setItem(row, 4, self.to_item(stock.open_amount))
            self.table_open_orders.setItem(row, 5, self.to_item_plain(stock.order_number))
            self.table_open_orders.setItem(row, 6, self.to_item_plain(stock.original_order_number))
            self.table_open_orders.setItem(row, 7, self.to_item(stock.order_price))
            self.table_open_orders.setItem(row, 8, self.to_item(stock.executed_price))
            self.table_open_orders.setItem(row, 9, self.to_item(stock.order_position))
            self.table_open_orders.setItem(row, 10, self.to_item(stock.order_state))
        self.table_open_orders.sortItems(1, Qt.DescendingOrder)

    def display_balance(self):
        self.clear_table(self.table_balance)
        for row, stock in enumerate(self.kiwoom.balance.values()):
            self.table_balance.insertRow(row)
            self.table_balance.setRowHeight(row, 8)
            self.table_balance.setItem(row, 0, self.to_item(stock.item_name))
            self.table_balance.setItem(row, 1, self.to_item(stock.current_price))
            self.table_balance.setItem(row, 2, self.to_item(stock.reference_price))
            self.table_balance.setItem(row, 3, self.to_item(stock.purchase_price_avg))
            self.table_balance.setItem(row, 4, self.to_item(stock.holding_amount))
            self.table_balance.setItem(row, 5, self.to_item(stock.purchase_sum))
            self.table_balance.setItem(row, 6, self.to_item_sign(stock.purchase_amount_net))
            self.table_balance.setItem(row, 7, self.to_item_sign(stock.balance_profit_net))
            self.table_balance.setItem(row, 8, self.to_item_sign(stock.balance_profit_rate))
            self.table_balance.setItem(row, 9, self.to_item_sign(stock.balance_profit_realization))
        self.table_balance.sortItems(0, Qt.DescendingOrder)

    def display_order_history(self):
        self.clear_table(self.table_order_history)
        for row, stock in enumerate(self.kiwoom.order_history.values()):
            self.table_order_history.insertRow(row)
            self.table_order_history.setRowHeight(row, 8)
            self.table_order_history.setItem(row, 0, self.to_item(stock.item_name))
            self.table_order_history.setItem(row, 1, self.to_item_time(stock.order_executed_time))
            self.table_order_history.setItem(row, 2, self.to_item(stock.order_amount))
            self.table_order_history.setItem(row, 3, self.to_item(stock.executed_amount))
            self.table_order_history.setItem(row, 4, self.to_item(stock.open_amount))
            self.table_order_history.setItem(row, 5, self.to_item_plain(stock.order_number))
            self.table_order_history.setItem(row, 6, self.to_item_plain(stock.original_order_number))
            self.table_order_history.setItem(row, 7, self.to_item(stock.order_price))
            self.table_order_history.setItem(row, 8, self.to_item(stock.executed_price))
            self.table_order_history.setItem(row, 9, self.to_item(stock.order_position))
            self.table_order_history.setItem(row, 10, self.to_item(stock.order_state))

    def clear_table(self, table):
        for row in range(table.rowCount()):
            table.removeRow(0)

    def get_order_history(self):
        item_code = self.cbb_item_code.currentText()
        self.kiwoom.request_order_history(item_code)

    def send_order(self):
        item_code = self.cbb_item_code.currentText()
        order_position = self.cbb_order_position.currentText()
        price = self.sb_price.value()
        amount = self.sb_amount.value()
        order_type = ORDER_TYPE[self.cbb_order_type.currentText()]
        order_number = self.le_order_number.text()

        self.kiwoom.order(item_code, price, amount, order_position, order_type, order_number)

    def on_select_account(self, account):
        self.kiwoom.account_number = int(account)

    def on_select_item_code(self, item_code):
        item_name = CODES.get(item_code)
        if item_name is None:
            item_name = self.kiwoom.get_item_name(item_code)
            if item_name != '':
                CODES[item_code] = item_name
                self.cbb_item_code.addItem(item_code)
                self.cbb_item_name.addItem(item_name)

        self.cbb_item_name.setCurrentText(item_name)
        self.update_order_variables()

    def on_select_item_name(self, index):
        item_name = self.cbb_item_name.currentText()
        item_code = self.kiwoom.get_item_code(item_name)
        self.cbb_item_code.setCurrentText(item_code)

    def on_add_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code in self.kiwoom.trading_items:
            return

        row = len(self.kiwoom.trading_items)
        self.table_trading_items.insertRow(row)
        self.table_trading_items.setRowHeight(row, 8)

        stock = Stock()
        stock.item_code = item_code
        stock.item_name = item_name
        self.kiwoom.trading_items[item_code] = stock
        self.display_trading_items()
        self.kiwoom.demand_trading_item_info(item_code)
        self.kiwoom.log(stock.item_name, 'trading information begins to be monitored')

    def on_remove_item(self):
        item_code = self.cbb_item_code.currentText()
        item_name = self.cbb_item_name.currentText()
        if item_code not in self.kiwoom.trading_items:
            return

        self.table_trading_items.removeRow(0)

        self.kiwoom.init_screen(item_code)
        del self.kiwoom.trading_items[item_code]
        self.table_trading_items.clearContents()
        self.display_trading_items()
        self.kiwoom.log(item_name, 'stock information monitoring is finished')

    def on_select_portfolio_table(self, row, column):
        column_count = self.table_portfolio.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_portfolio.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_portfolio.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 1
        current_price_item = self.table_portfolio.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

    def on_select_trading_items_table(self, row, column):
        column_count = self.table_trading_items.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_trading_items.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_trading_items.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 2
        current_price_item = self.table_trading_items.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

    def on_select_open_orders_table(self, row, column):
        column_count = self.table_order_history.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_open_orders.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_open_orders.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        open_amount_column = 4
        open_amount_item = self.table_open_orders.item(row, open_amount_column)
        open_amount = int(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

        order_number_column = 5
        order_number_item = self.table_open_orders.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 7
        order_price_item = self.table_open_orders.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

    def on_select_balance_table(self, row, column):
        column_count = self.table_balance.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_balance.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_balance.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        current_price_column = 1
        current_price_item = self.table_balance.item(row, current_price_column)
        current_price = self.process_type(current_price_item.text())
        self.sb_price.setValue(current_price)

    def on_select_order_history_table(self, row, column):
        column_count = self.table_order_history.columnCount() - 1
        selection_range = QTableWidgetSelectionRange(row, 0, row, column_count)
        self.table_order_history.setRangeSelected(selection_range, True)

        item_name_column = 0
        item_name_item = self.table_order_history.item(row, item_name_column)
        item_name = item_name_item.text()
        index = self.cbb_item_name.findText(item_name)
        self.cbb_item_name.setCurrentIndex(index)

        open_amount_column = 4
        open_amount_item = self.table_order_history.item(row, open_amount_column)
        open_amount = self.process_type(open_amount_item.text())
        self.sb_amount.setValue(open_amount)

        order_number_column = 5
        order_number_item = self.table_order_history.item(row, order_number_column)
        order_number = order_number_item.text()
        self.le_order_number.setText(order_number)

        order_price_column = 7
        order_price_item = self.table_order_history.item(row, order_price_column)
        order_price = self.process_type(order_price_item.text())
        self.sb_price.setValue(order_price)

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

    def on_kiwoom_signal(self, signal, *args):
        if signal == 'deposit':
            self.update_deposit_info()
        elif signal == 'portfolio':
            self.update_order_variables()
        elif signal == 'portfolio_table':
            self.display_portfolio()
        elif signal == 'trading_items_table':
            self.display_trading_items()
        elif signal == 'open_orders_table':
            self.display_open_orders()
        elif signal == 'balance_table':
            self.display_balance()
        elif signal == 'order_history_table':
            self.display_order_history()

    def on_kiwoom_log(self, *args):
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
        self.kiwoom.log('Closing process initializing...')
        self.kiwoom.close_process()
        self.kiwoom.clear()
        self.kiwoom.deleteLater()
        self.deleteLater()