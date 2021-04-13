from wookutil import WookLog

class WookChart(WookLog):
    def __init__(self, log, broker):
        super().__init__()
        WookLog.custom_init(self, log)
        self.prices = broker.chart_prices

    def update(self):


    def get_moving_average(self):
        pass