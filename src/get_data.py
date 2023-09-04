import datetime
from datetime import timedelta
import pandas as pd
import re
import json
import requests
from io import StringIO
import yfinance as yf
import numpy as np
import plotly.graph_objs as go
from stock_const import stock_list

class GetStockPrice:
    def __init__(self) -> None:
        pass
    
    def get_live_exchange_rate(self):
        live_data = yf.download(tickers='CADUSD=X', period ='3m', interval='1m')['Close'].tolist()[-1]
        return 1/live_data

    def get_live_stock_price(self, ticker):
        '''
        Returns stock price in the nearest minute
        '''
        live_data = yf.download(tickers=ticker, period ='1d', interval='1m')['Close'].tolist()[-1]
        return live_data
    
    def get_historical_close_price(self, ticker, date):
        '''
        date in the string format of YYYYMMDD
        Returns close price of date for ticker
        '''
        data = yf.download(tickers=ticker, period ='2y', interval='1d')
        data = data.reset_index()
        data['Date_adj'] = data['Date'].dt.strftime('%Y%m%d')
        while date not in data['Date_adj'].tolist():
            date = (datetime.datetime.strptime(date, '%Y%m%d')- timedelta(days=1)).strftime('%Y%m%d')
        close = data[data['Date_adj'] == date]['Close'].tolist()[0]
        print(date)
        print(close)
        return close

    def get_historical_open_price(self, ticker, date):
        '''
        date in the string format of YYYYMMDD
        Returns close price of date for ticker
        '''
        prev_flag = False
        data = yf.download(tickers=ticker, period ='2y', interval='1d')
        data = data.reset_index()
        data['Date_adj'] = data['Date'].dt.strftime('%Y%m%d')
        while date not in data['Date_adj'].tolist():
            date = (datetime.datetime.strptime(date, '%Y%m%d')- timedelta(days=1)).strftime('%Y%m%d')
            prev_flag = True
        if not prev_flag:
            open = data[data['Date_adj'] == date]['Open'].tolist()[0]
        else:
            open = data[data['Date_adj'] == date]['Close'].tolist()[0]
        print(date)
        print(open)
        return open
    
    def get_book_cost(self, buy_price, quantity, brokerfee, buy_currency):
        book_cost = buy_price * quantity + brokerfee
        if buy_currency == 'USD':
            # TODO: make that live!
            book_cost = book_cost * self.get_live_exchange_rate()
        return book_cost

    def get_market_value_in_CAD(self, ticker, date, quantity, buy_currency, close_flag=True):
        if close_flag:

            market_value = self.get_historical_close_price(ticker, date) * quantity
        else:
            market_value = self.get_historical_open_price(ticker, date) * quantity
        if buy_currency == 'USD':
            # TODO: make that live!
            market_value = market_value * self.get_live_exchange_rate()
        return market_value

    def get_portfolio_return(self, stock_list, start_date, end_date):
        '''
        Returns period return and capital gain
        '''

        # Return table for period
        start_date_prev = (datetime.datetime.strptime(start_date, '%Y%m%d')- timedelta(days=1)).strftime('%Y%m%d')
        portfolio_dict = {'股票代码':[], '实时价格':[], '时间段':[], '时间段收盘价格': [], '数量':[], '市场价值':[], '资本利得':[], '收益百分比':[]}
        since_inception_portfolio_dict = {'股票代码':[], '实时价格':[], '购买价格':[], '总成本': [], '数量':[], '当前市场价值':[], '资本利得':[], '收益百分比':[]}

        

        total_gain = 0
        total_live_gain = 0
        initial_value = 0
        total_book_cost = 0
        
        for stock in stock_list:
            # define variables
            ticker = stock['Ticker']
            print(ticker)
            buy_date = stock['Buy_Date']
            buy_price = stock['Buy_Price']
            quantity = stock['Quantity']
            buy_currency = stock['Buy_Currency']
            brokerfee = stock['Brokerfee']
            sell_date = stock['Sell_Date']

            
            book_cost = self.get_book_cost(buy_price, quantity, brokerfee, buy_currency)
            live_price = self.get_live_stock_price(ticker)
            market_value_start_date = self.get_market_value_in_CAD(ticker, start_date_prev, quantity, buy_currency, True)
            market_value_end_date = self.get_market_value_in_CAD(ticker, end_date, quantity, buy_currency, True)

            if datetime.datetime.strptime(start_date, '%Y%m%d') <= datetime.datetime.strptime(buy_date, '%Y%m%d'):
                market_value_start_date = book_cost
            # TO: add sell book cost
            # if sell_date!='':
            #     if datetime.datetime.strptime(end_date, '%Y%m%d') > datetime.datetime.strptime(sell_date, '%Y%m%d'):
            #         
                    
            gain = market_value_end_date - market_value_start_date
            total_gain += gain
            
            initial_value += market_value_start_date
            portfolio_dict['股票代码'] += [ticker]
            portfolio_dict['实时价格'] += [live_price]
            portfolio_dict['时间段'] += [[start_date, end_date]]
            portfolio_dict['时间段收盘价格'] += [self.get_historical_close_price(ticker, end_date)]
            portfolio_dict['数量'] += [quantity]
            portfolio_dict['市场价值'] += ["{:.2f}".format(market_value_end_date)]
            portfolio_dict['资本利得'] += ["{:.2f}".format(gain)]
            portfolio_dict['收益百分比'] += ["{:.2f}".format(gain/market_value_start_date)]

        

            #Return since inception
            

            live_gain = market_value_end_date - book_cost
            since_inception_portfolio_dict['股票代码'] += [ticker]
            since_inception_portfolio_dict['实时价格'] += [live_price]
            since_inception_portfolio_dict['购买价格'] += [buy_price]
            since_inception_portfolio_dict['总成本'] += [book_cost]
            since_inception_portfolio_dict['数量'] += [quantity]
            since_inception_portfolio_dict['当前市场价值'] += ["{:.2f}".format(market_value_end_date)]
            since_inception_portfolio_dict['资本利得'] += ["{:.2f}".format(live_gain)]
            since_inception_portfolio_dict['收益百分比'] += ["{:.2f}".format(live_gain/market_value_start_date)]
            total_live_gain += live_gain
            total_book_cost += book_cost

        df1 = pd.DataFrame(data=portfolio_dict)
        period_return = total_gain/initial_value
        period_return_percentage = "{:.2%}".format(period_return)
        total_gain = "{:.2f}".format(total_gain)

        df2 = pd.DataFrame(data=since_inception_portfolio_dict)
        
        live_return = total_live_gain/total_book_cost
        live_return_percentage = "{:.2%}".format(live_return)
        total_live_gain = "{:.2f}".format(total_live_gain)

        return df1, period_return_percentage, total_gain, df2, total_live_gain, live_return_percentage



            
getstockprice = GetStockPrice()
df1, period_return_percentage, total_gain, df2, live_gain, live_return_percentage = getstockprice.get_portfolio_return(stock_list, '20210219', '20220412')


print(df1)

print("时间段内资本利得: " + str(total_gain))
print("时间段内收益百分比: " + period_return_percentage)

print(df2)
print("总资本利得: " + str(live_gain))
print("总收益百分比: " + live_return_percentage)      
df2.to_csv('live.csv')


