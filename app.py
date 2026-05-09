from ib_insync import *
import time

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 128

ib = IB()
ib.connect(HOST, PORT, clientId=CLIENT_ID)

contract = Forex("AUDUSD")
ib.qualifyContracts(contract)

ticker = ib.reqMktData(contract)

def on_ticker_update(t):
    print(f"AUD/USD | Bid: {t.bid:.5f} | Ask: {t.ask:.5f} | Last: {t.last:.5f}")

ticker.updateEvent += on_ticker_update

time.sleep(3)

order = MarketOrder("BUY", 1000)
trade = ib.placeOrder(contract, order)

def on_order_status(trade_obj):
    if trade_obj.orderStatus.status == "Filled":
        fill = trade_obj.fills[0]
        print(f"FILLED: {fill.execution.shares} @ {fill.execution.price:.5f}")

trade.statusEvent += on_order_status

try:
    while True:
        ib.sleep(1)
except KeyboardInterrupt:
    ib.cancelMktData(contract)
    ib.disconnect()