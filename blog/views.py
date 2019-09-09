from django.shortcuts import render
from django.http import HttpResponse
from .models import Ticker
import bs4 as bs
import pandas as pd
import requests
from django.http import JsonResponse
import time
import io
from alpha_vantage.timeseries import TimeSeries
from mpl_finance import candlestick_ohlc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pytz import timezone
import itertools
from matplotlib import style
import os
from bs4 import BeautifulSoup
import re
from json import loads
from pandas.tseries.offsets import BDay
import datetime as DT
from .models import TickerLogger

import json
from .stocker import Stocker

posts = [
    {
        'author': 'CoreyMs',
        'title': 'Blog Post 1',
        'content': 'First post content',
        'date_posted': 'August 27, 2018'
    },

    {
        'author': 'Jane doe',
        'title': 'Blog Post 2',
        'content': 'First post content 2',
        'date_posted': 'August 28, 2018'
    }

]

my_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_cookie_crumb(symbol):
    cookie, lines = get_page_data(symbol)
    crumb = split_crumb_store(find_crumb_store(lines))
    # Note: possible \u002F value
    # ,"CrumbStore":{"crumb":"FWP\u002F5EFll3U"
    # FWP\u002F5EFll3U
    # crumb2 = crumb.decode('unicode-escape')

    return cookie, crumb


def split_crumb_store(v):
    return v.split(':')[2].strip('"')


def find_crumb_store(lines):
    # Looking for
    # ,"CrumbStore":{"crumb":"9q.A4D1c.b9
    for l in lines:
        if re.findall(r'CrumbStore', l):
            return l
    print("Did not find CrumbStore")


def get_cookie_value(r):
    return {'B': r.cookies['B']}


def get_page_data(symbol):
    url = "https://finance.yahoo.com/quote/%s/?p=%s" % (symbol, symbol)
    r = requests.get(url)
    cookie = get_cookie_value(r)
    # lines = r.text.encode('utf-8').strip().replace('}', '\n')
    lines = r.content.decode('unicode-escape').strip().replace('}', '\n')
    return cookie, lines.split('\n')


def get_now_epoch():
    # @see https://www.linuxquestions.org/questions/programming-9/python-datetime-to-epoch-4175520007/#post5244109
    return int(time.time())


def avg_true_range(df):
    ind = range(0, len(df))
    indexlist = list(ind)
    df.index = indexlist

    for index, row in df.iterrows():
        if index != 0:
            tr1 = row["High"] - row["Low"]
            tr2 = abs(row["High"] - df.iloc[index - 1]["Close"])
            tr3 = abs(row["Low"] - df.iloc[index - 1]["Close"])

            true_range = max(tr1, tr2, tr3)
            df.set_value(index, "TrueRange", true_range)

    df["AvgTR"] = df["TrueRange"].rolling(min_periods=14, window=14, center=False).mean()
    return df


def data_analysis(request):
    if request.method == 'GET':
        try:

            bday_15 = (pd.datetime.today() - BDay(17)).date()

            hiredate = '2019-01-20'
            pattern = '%Y-%m-%d'
            epoch_start = int(time.mktime(time.strptime(bday_15.strftime('%Y-%m-%d'), pattern)))

            # start_date = 1544832000
            start_date = epoch_start
            end_date = get_now_epoch()

            stock = request.GET['tcker']
            time_frame = request.GET['radiovalue']
            print('Currently Pulling', stock)

            intval = time_frame + 'min'

            # get live price of Apple
            # si.get_live_price(stock)

            # yahoo = Share(stock)
            #
            # print (yahoo.get_price())

            if time_frame == '15D':
                print('Currently Pulling', stock)
                cookie, crumb = get_cookie_crumb(stock)

                url = "https://query1.finance.yahoo.com/v7/finance/download/%s?period1=%s&period2=%s&interval=1d&events=history&crumb=%s" % (
                    stock, start_date, end_date, crumb)
                response = requests.get(url, cookies=cookie)

                urldata = response.content
                df = pd.read_csv(io.StringIO(urldata.decode('utf-8')))

                df.set_index('Date', inplace=True)

                avg_true_range(df)

                df["AvgTR"].fillna(0, inplace=True)
                df["TrueRange"].fillna(0, inplace=True)

                LL = PPSR(df)

                dict = LL.to_dict('list')

                my_curr_stock = get_current_price(stock)

                dict['Price'] = my_curr_stock['Price']

                dict['stock_strong'] = my_curr_stock['stock_strong']

            else:
                ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
                data, meta_data = ts.get_intraday(symbol=stock, interval=intval, outputsize='compact')

                # data_min, meta_data_min = ts.get_intraday(symbol=stock, interval='1min', outputsize='compact')

                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

                avg_true_range(data)

                data["AvgTR"].fillna(0, inplace=True)
                data["TrueRange"].fillna(0, inplace=True)

                MM = PPSR(data)

                dict = MM.to_dict('list')

                my_curr_stock = get_current_price(stock)

                dict['Price'] = my_curr_stock['Price']

                dict['stock_strong'] = my_curr_stock['stock_strong']

            return JsonResponse(dict)

        except Exception as e:
            print(str(e), 'failed to organize pulled data.')
        except Exception as e:
            print(str(e), 'failed to pull pricing data')

    return HttpResponse("Request method is not a GET")


def graph_data(data, stock):
    fontsizes = itertools.cycle([8, 16, 24, 32])

    # df_volume = data['Volume'].resample('10D').sum()

    # data.index = pd.to_datetime(data.index, unit='s')

    # style.use('dark_background')
    style.use('seaborn-bright')

    data2 = data.copy()

    data2.reset_index(inplace=True)

    data2.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    data2['Date'] = pd.to_datetime(data2['Date'])
    data2['Date'] = data2['Date'].map(mdates.date2num)

    # df_volume = data['Volume'].resample('10D').sum()

    plt.clf()

    # fig = plt.figure(facecolor='#07000d')
    ax1 = plt.subplot2grid((1, 1), (0, 0))

    ax1.clear()
    # ax1 = plt.subplot2grid((6, 1), (0, 0), rowspan=5, colspan=1)

    time_format = '%m/%d/%Y %H:%M'

    data2 = data2.iloc[90:]

    # data['Date'] = data.index
    # data['Date'] = pd.to_datetime(data['Date'])
    # data['Date'] = data["Date"].apply(mdates.date2num)
    #
    # dates = data["Date"].tolist()
    # openp = data["Open"].tolist()
    # highp = data["High"].tolist()
    # lowp = data["Low"].tolist()
    # closep = data["Close"].tolist()
    # volume = data["Volume"].tolist()
    #
    # x = 0
    # y = len(dates)
    # ohlc = []
    #
    # while x < y:
    #     append_me = dates[x], openp[x], highp[x], lowp[x], closep[x], volume[x]
    #     ohlc.append(append_me)
    #     x += 1
    #
    # # candlestick_ohlc(ax1, ohlc)
    #
    # candlestick_ohlc(ax1, ohlc, width=.6/(24*60), colorup='#77d879', colordown='#db3f3f')
    #
    # for label in ax1.xaxis.get_ticklabels():
    #     label.set_rotation(90)

    candlestick_ohlc(ax1, data2.values, width=.6 / (24 * 60), colorup='#77d879', colordown='#db3f3f')

    # width = .6 / (24 * 60)

    ax1.xaxis_date()
    # ax1.xaxis.set_major_formatter(mdates.DateFormatter(time_format))
    # ax1.xaxis.set_major_locator(mticker.MaxNLocator(11))
    # ax1.xaxis.set_major_locator(mticker.MaxNLocator(11))
    # ax1.grid(True)  # , color='g', linestyle='-', linewidth=5)
    plt.xticks(rotation=45)

    plt.ylabel('Stock Price', rotation=90)
    plt.xlabel('Date Hours:Minutes')
    plt.title(stock.upper())
    # plt.legend()
    # plt.subplots_adjust(left=0.09, bottom=0.20, right=0.94, top=0.90, wspace=0.2, hspace=0)

    plt.subplots_adjust(left=0.09, bottom=0.20, right=0.94, top=0.90, wspace=0.2, hspace=0)

    plt.savefig(my_path + '/static/mychart.png')
    plt.close()

    # plt.show()


def get_volume_intraday(request):
    if request.method == 'GET':
        try:
            stock = request.GET['tcker']
            ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
            data, meta_data = ts.get_intraday(symbol=stock, interval='1min', outputsize='compact')

            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            graph_data(data, stock)

            # dropping passed columns
            data.drop(["Open", "High", "Low"], axis=1, inplace=True)

            data.sort_index(inplace=True, ascending=False)

            # Converting the index as date
            data.index = pd.to_datetime(data.index)

            data.index = data.index.strftime('%m/%d/%Y %H:%M:%S')

            json_response = data.to_json(orient='split')

            dict = data.to_dict('list')

            # return JsonResponse(json_response)

            return HttpResponse(json_response, content_type='application/json')

        except Exception as e:
            print(str(e), 'failed to organize pulled data.')
        except Exception as e:
            print(str(e), 'failed to pull pricing data')

    return HttpResponse("Request method is not a GET")


def PPSR(data):
    PP = pd.Series((data['High'] + data['Low'] + data['Close']) / 3)
    R1 = pd.Series(2 * PP - data['Low'])
    S1 = pd.Series(2 * PP - data['High'])
    R2 = pd.Series(PP + data['High'] - data['Low'])
    S2 = pd.Series(PP - data['High'] + data['Low'])
    R3 = pd.Series(data['High'] + 2 * (PP - data['Low']))
    S3 = pd.Series(data['Low'] - 2 * (data['High'] - PP))
    VWAP = (data.Volume * (data.High + data.Low) / 2).cumsum() / data.Volume.cumsum()
    psr = {'PP': PP, 'R1': R1, 'S1': S1, 'R2': R2, 'S2': S2, 'R3': R3, 'S3': S3, 'VWAP': VWAP}
    PSR = pd.DataFrame(psr)
    data = data.join(PSR)
    return data


def load_sec_fillings(request):
    company_name_url = ''
    name_noinc = ''
    mydict = {}
    if request.method == 'GET':
        try:
            stock = request.GET['tcker']

            comp_prop = get_current_price(stock)

            company = comp_prop['Company']

            if (company.find(",") != -1 and company.find("Inc") != -1 and company.find(",") + 2 == company.find(
                    "Inc")) or \
                    company.find("Inc.") != -1:

                new_string = re.sub("[ ,.]", " ", company)
                company_name_url_list = new_string.split()

                i = 0
                for word in company_name_url_list:
                    if word == 'Inc':
                        name_noinc = company_name_url
                        company_name_url = company_name_url + '%2C+' + word
                    else:
                        if i == len(company_name_url_list) - 2:
                            company_name_url = company_name_url + word
                        else:
                            company_name_url = company_name_url + word + '+'
                    i += 1

            if company.find("Corporation") != -1 or company.find("Corp.") != -1:
                new_string = re.sub("[ ,.]", " ", company)
                company_name_url_list = new_string.split()

                i = 0
                for word in company_name_url_list:
                    if word != 'Corporation' and word != 'Corp':
                        if i == len(company_name_url_list) - 2:
                            company_name_url = company_name_url + word
                        else:
                            company_name_url = company_name_url + word + '+'
                    i += 1

            sec_fillings = f"https://www.sec.gov/cgi-bin/browse-edgar?company=" + company_name_url + "&owner=exclude&action=getcompany"
            soup = BeautifulSoup(requests.get(sec_fillings).text, "html.parser")

            tab = soup.find("table", {"class": "tableFile2"})

            if tab is None:
                sec_fillings = f"https://www.sec.gov/cgi-bin/browse-edgar?company=" + name_noinc + "&owner=exclude&action=getcompany"
                soup = BeautifulSoup(requests.get(sec_fillings).text, "html.parser")

                tab = soup.find("table", {"class": "tableFile2"})

                if tab is None:
                    return HttpResponse(mydict, content_type='application/json')

            table_rows = tab.find_all('tr')

            res = []
            j = 0
            for tr in table_rows:
                if j <= 3:
                    td = tr.find_all('td')
                    row = [tr.text.strip() for tr in td if tr.text.strip()]
                    if row:
                        res.append(row)

                j += 1

            df = pd.DataFrame(res, columns=['Filings', 'Format', 'Description', 'Filed', 'Number'])

            json_response = df.to_json(orient='split')

            return HttpResponse(json_response, content_type='application/json')

        except Exception as e:
            print(str(e), 'failed to organize pull SEC FILLINGS . - load_sec_fillings')
            return HttpResponse(mydict, content_type='application/json')
        except Exception as e:
            print(str(e), 'failed to pull SEC FILLINGS - load_sec_fillings')
            return HttpResponse(mydict, content_type='application/json')

    return HttpResponse(mydict, content_type='application/json')


def get_change_percentage(numvaluestart, numvaluecurrent):
    floatpricestart = float(numvaluestart)
    floatpricecurrent = float(numvaluecurrent)

    return round(((floatpricecurrent - floatpricestart) / floatpricestart) * 100, 2)


def get_current_price(ticker):
    stock_company = f"https://finance.yahoo.com/quote/" + ticker
    soup = BeautifulSoup(requests.get(stock_company).text, "html.parser")
    name = soup.h1.text.split('-')[1].strip()
    price = soup.select_one('.Trsdu\(0\.3s\)').text
    volume = soup.find("td", text="Volume").find_next_sibling("td").text

    script = soup.find("script", text=re.compile("root.App.main")).text
    data = loads(re.search("root.App.main\s+=\s+(\{.*\})", script).group(1))
    stores = data["context"]["dispatcher"]["stores"]

    stock_properties = stores[u'QuoteSummaryStore']

    try:
        premarketprice = 0.00
        regularmarketprice = stock_properties['price']['regularMarketPrice']['fmt']
        postmarketprice = stock_properties['price']['postMarketPrice']['fmt']
        regularmarkethigh = stock_properties['summaryDetail']['regularMarketDayHigh']['fmt']
        previous_close = stock_properties['summaryDetail']['regularMarketPreviousClose']['fmt']

        fiftytwoweekhigh = stock_properties['summaryDetail']['fiftyTwoWeekHigh']['fmt']
        regularMarketOpen = stock_properties['summaryDetail']['regularMarketOpen']['fmt']
        regularMarketVolume = stock_properties['summaryDetail']['regularMarketVolume']['fmt']

        float_volume = float(regularMarketVolume[:-1])

        est = timezone('US/Eastern')

        current_time = datetime.now(est).time()

        test_time = DT.datetime.now()

        today800am = test_time.replace(hour=8, minute=00, second=0, microsecond=0).time()
        today929am = test_time.replace(hour=9, minute=29, second=0, microsecond=0).time()
        today930am = test_time.replace(hour=9, minute=30, second=0, microsecond=0).time()
        today400pm = test_time.replace(hour=16, minute=0, second=0, microsecond=0).time()

        if today800am == current_time <= today929am:
            premarketprice = stock_properties['price']['preMarketPrice']['fmt']
            price = premarketprice
        elif today930am == current_time <= today400pm:
            price = regularmarketprice
        else:
            price = postmarketprice

        # if current_time >= today800am and current_time < today929am:
        #     premarketprice = stock_properties['price']['preMarketPrice']['fmt']
        #     price = premarketprice
        # elif current_time >= today930am and current_time <= today400pm:
        #     price = regularmarketprice
        # else:
        #     price = postmarketprice

        stock_strong = 'N'

        if float_volume > 1.99 and regularMarketVolume[-1] == 'M':
            if regularMarketOpen > previous_close:
                percentage_change_open = get_change_percentage(previous_close, regularMarketOpen)

                if percentage_change_open >= 3.00:
                    percentage_change_current = get_change_percentage(regularMarketOpen, price)

                    if percentage_change_current >= 10.00:
                        if regularmarkethigh > price:
                            percentage_change_high = get_change_percentage(price, regularmarkethigh)

                            if 0.00 == percentage_change_high <= 1.50:
                                stock_strong = 'Y'

    except Exception as e:
        postmarketprice = price
        premarketprice = price
        regularmarketprice = price
        regularmarkethigh = 0.00
        previous_close = 0.00

    my_ticker_dict = {'Company': name, 'Price': price, 'Volume': volume, 'RegularMarketPrice': regularmarketprice,
                      'PostMarketPrice': postmarketprice, 'PreMarketPrice': premarketprice,
                      'MarketHigh': regularmarkethigh, 'Previous_Close': previous_close, 'stock_strong': stock_strong,
                      'fiftytwo_week_high': fiftytwoweekhigh}

    return my_ticker_dict


def data_calculations(request):
    if request.method == 'GET':

        stock = request.GET['tcker']

        print('Currently Pulling', stock)

        # soup = bs(res.content, 'lxml')
        # price = soup.select_one('.Trsdu\(0\.3s\)').text

        # stock_company = f"https://finance.yahoo.com/quote/" + stock
        # soup = BeautifulSoup(requests.get(stock_company).text, "lxml")
        # name = soup.h1.text.split('-')[1].strip()
        # price = soup.select_one('.Trsdu\(0\.3s\)').text
        # volume = soup.find("td", text="Volume").find_next_sibling("td").text

        # ticker_data_url = f"https://query1.finance.yahoo.com/v8/finance/chart/"+stock+"?region=US&lang=en-US&includePrePost=false&interval=2m&range=1d&corsDomain=finance.yahoo.com&.tsrc=finance"
        # ticker_data = json.loads(requests.get(ticker_data_url).text)
        # price = ticker_data['chart']['result'][0]['meta']['previousClose']

        # hiredate = '2018-10-28'
        # pattern = '%Y-%m-%d'
        # epoch_start = int(time.mktime(time.strptime(hiredate, pattern)))

        bday_20 = (pd.datetime.today() - BDay(20)).date()

        hiredate = '2019-01-20'
        pattern = '%Y-%m-%d'
        epoch_start = int(time.mktime(time.strptime(bday_20.strftime('%Y-%m-%d'), pattern)))

        # start_date = 1544832000
        start_date = epoch_start
        end_date = get_now_epoch()

        try:

            # ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
            # data, meta_data = ts.get_intraday(symbol=stock, interval='1min', outputsize='full')

            cookie, crumb = get_cookie_crumb(stock)

            url = "https://query1.finance.yahoo.com/v7/finance/download/%s?period1=%s&period2=%s&interval=1d&events=history&crumb=%s" % (
                stock, start_date, end_date, crumb)
            response = requests.get(url, cookies=cookie)
            stockFile = []

            splitSource = response.text.split('\n')

            urlData = response.content
            df = pd.read_csv(io.StringIO(urlData.decode('utf-8')))

            df.set_index('Date', inplace=True)

            avg_true_range(df)

            df["AvgTR"].fillna(0, inplace=True)
            df["TrueRange"].fillna(0, inplace=True)

            # compute and print the data

            LL = PPSR(df)

            # data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            #
            # data['vwap_pandas'] = (data.Volume * (data.High + data.Low) / 2).cumsum() / data.Volume.cumsum()
            #
            # v = data.Volume.values
            # h = data.High.values
            # l = data.Low.values
            #
            # data['vwap_numpy'] = np.cumsum(v * (h + l) / 2) / np.cumsum(v)

            # data['vwap_numba'] = vwap()

            # MM = PPSR(data)

            dict = LL.to_dict('list')

            my_curr_stock = get_current_price(stock)

            dict['Price'] = my_curr_stock['Price']

            return JsonResponse(dict)

        except Exception as e:
            print(str(e), 'failed to organize pulled data.')
        except Exception as e:
            print(str(e), 'failed to pull pricing data')

    return HttpResponse("Request method is not a GET")


def data_calculations2(stock):
    print('Currently Pulling', stock)

    hiredate = '2018-10-15'
    pattern = '%Y-%m-%d'
    epoch_start = int(time.mktime(time.strptime(hiredate, pattern)))

    # start_date = 1544832000
    start_date = epoch_start
    end_date = get_now_epoch()

    try:

        cookie, crumb = get_cookie_crumb(stock)

        url = "https://query1.finance.yahoo.com/v7/finance/download/%s?period1=%s&period2=%s&interval=1d&events=history&crumb=%s" % (
            stock, start_date, end_date, crumb)
        response = requests.get(url, cookies=cookie)
        stockFile = []

        splitSource = response.text.split('\n')

        urlData = response.content
        df = pd.read_csv(io.StringIO(urlData.decode('utf-8')))

        df.set_index('Date', inplace=True)

        # compute and print the data
        return PPSR(df)

    except Exception as e:
        print(str(e), 'failed to organize pulled data.')
    except Exception as e:
        print(str(e), 'failed to pull pricing data')


def load_finviz_no_volume():
    # resp = requests.get('https://finviz.com/')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
    resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5&c=1,25,30,49,59,63,65,67')
    # resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5,sh_curvol_o200&c=1,25,30,49,59,63,65,67')

    est = timezone('US/Eastern')
    print("Time in EST:", datetime.now(est).hour)

    soup = bs.BeautifulSoup(resp.text, 'html.parser')
    table_other = soup.find(text="Float").find_parent("table")
    table_rows = table_other.find_all('tr')
    res = []
    for tr in table_rows:
        td = tr.find_all('td')
        row = [tr.text.strip() for tr in td if tr.text.strip()]
        if row:
            res.append(row)

    res.pop(0)
    df = pd.DataFrame(res, columns=['Ticker', 'Float', 'FloatShort', 'ATR', 'RSI', 'AvgVolume', 'Price', 'Volume'])

    return df


def load_finviz():
    try:
        # resp = requests.get('https://finviz.com/')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
        # resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5&c=1,25,30,49,59,63,65,67')

        resp = requests.get(
            'https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u7,sh_curvol_o200&o=sharesfloat&c=1,25,30,49,59,63,65,67')  # D.R. Modified Screener URL 04/03/2019

        # resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5,sh_curvol_o200&c=1,25,30,49,59,63,65,67')

        soup = bs.BeautifulSoup(resp.text, 'html.parser')
        # table = soup.find('table', {'class':'t-home-table'})
        # table = soup.find('div', {'id':'screener-content'})
        # table_rows = table.find_all('tr')

        table_other = soup.find(text="Float").find_parent("table")
        table_rows = table_other.find_all('tr')

        # table_div = soup.find('div', {'id': 'screener-content'})
        # table = table_div.find('table')
        # table_screener = table.find('table')
        # table_rows = table_screener.find_all('tr')

        res = []
        for tr in table_rows:
            td = tr.find_all('td')
            row = [tr.text.strip() for tr in td if tr.text.strip()]
            if row:
                res.append(row)

        res.pop(0)
        df = pd.DataFrame(res, columns=['Ticker', 'Float', 'FloatShort', 'ATR', 'RSI', 'AvgVolume', 'Price', 'Volume'])

        # dataframe_collection = {}
        #
        # for index, row in df.iterrows():
        #     dataframe_collection[index] = data_calculations(row['Ticker'])

        # df = pd.DataFrame(res)
        # df.columns = df.iloc[0]
        # df = df.drop(df.index[0])

        return df

    except Exception as e:
        print(str(e), 'Loading load_finviz_no_volume.')
        return load_finviz_no_volume()


def load_tickers(request):
    if request.method == 'GET':

        # resp = requests.get('https://finviz.com/')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
        # resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5&c=1,25,30,59,63,67,65')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
        resp = requests.get(
            'https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5,sh_curvol_o200&c=1,25,30,59,63,67,65')
        soup = bs.BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', {'class': 't-home-table'})
        table_rows = table.find_all('tr')

        res = []
        for tr in table_rows:
            td = tr.find_all('td')
            row = [tr.text.strip() for tr in td if tr.text.strip()]
            if row:
                res.append(row)

        df = pd.DataFrame(res)
        df.columns = df.iloc[0]
        df = df.drop(df.index[0])

        dict = df.to_dict('list')

        # return df

        return JsonResponse(dict)

    return HttpResponse("Request method is not a GET")


def custom_screener(request):
    url_screener = request.GET['url']

    print('Currently Pulling', url_screener)

    resp = requests.get(url_screener)
    soup = bs.BeautifulSoup(resp.text, 'html.parser')
    table_other = soup.find(text="Float").find_parent("table")
    table_rows = table_other.find_all('tr')

    res = []
    for tr in table_rows:
        td = tr.find_all('td')
        row = [tr.text.strip() for tr in td if tr.text.strip()]
        if row:
            res.append(row)

    res.pop(0)
    df = pd.DataFrame(res, columns=['Ticker', 'Float', 'FloatShort', 'ATR', 'RSI', 'AvgVolume', 'Price', 'Volume'])

    json_response = df.to_json(orient='split')

    return HttpResponse(json_response, content_type='application/json')


def home(request):
    # ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
    # data, meta_data = ts.get_intraday(symbol='NBEV',interval='1min', outputsize='full')
    # data['4. close'].plot()
    # plt.title('Intraday Times Series for the MSFT stock (1 min)')
    # plt.show()

    df_finviz = load_finviz()

    # for index, row in df_finviz.iterrows():
    #     ticker_properties = get_current_price(row['Ticker'])
    #     row['Price'] = ticker_properties['Price']

    json = df_finviz.to_json()

    # dict = df_finviz.to_dict('list')

    df_finviz['Float'] = df_finviz['Float'].str[:-1]

    df_finviz[["Float"]] = df_finviz[["Float"]].apply(pd.to_numeric)

    df_finviz[["Price"]] = df_finviz[["Price"]].apply(pd.to_numeric)

    # df_finviz.sort_values(by=['Price'], inplace=True, ascending=True)

    dict = df_finviz.to_dict(orient='records')

    # microsoft = Stocker('PSTV')

    # microsoft = Stocker(ticker='FFHL')

    # model, model_data = microsoft.create_prophet_model()

    # microsoft.plot_stock()

    # Stocker.buy_and_hold(microsoft, start_date=None, end_date=None, nshares=100)

    # microsoft.predict_future(days=5)

    # Stocker.evaluate_prediction(microsoft,start_date=None, end_date=None, nshares=1000)

    context = {
        'data': df_finviz.to_html(),
        'symbols': dict

    }
    return render(request, 'blog/home.html', context)


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})


def search_filter(request):
    try:
        if request.method == 'GET':

            stock = request.GET['ticker']
            datestart = request.GET['datestart']
            dateend = request.GET['dateend']

            if stock and not datestart or not dateend:
                df = pd.DataFrame(
                    list(TickerLogger.objects.filter(ticker=stock).values()))

            if datestart and dateend and stock:
                start_date = datetime.strptime(datestart, '%m/%d/%Y')
                end_date = datetime.strptime(dateend, '%m/%d/%Y').replace(hour=23, minute=59, second=59)

                df = pd.DataFrame(
                    list(TickerLogger.objects.filter(ticker=stock, entrydate__gte=start_date,
                                                     entrydate__lt=end_date).values()))
            if datestart and dateend and not stock:
                start_date = datetime.strptime(datestart, '%m/%d/%Y')
                end_date = datetime.strptime(dateend, '%m/%d/%Y').replace(hour=23, minute=59, second=59)

                df = pd.DataFrame(
                    list(TickerLogger.objects.filter(entrydate__gte=start_date,
                                                     entrydate__lt=end_date).values()))
            df['profit'] = (df.exitprice * df.position) - (df.entryprice * df.position)
            df['cummpl'] = df.profit.cumsum()
            df['percentage'] = (((df.exitprice - df.entryprice) / df.entryprice) * 100)
            df['gapentry'] = (((df.entryprice - df.prevdayclose) / df.prevdayclose) * 100)
            df['equity'] = (df.entryprice * df.position)
            df['exitvalue'] = round((df.exitprice * df.position), 2)
            df['prevdayclose'] = df['prevdayclose'].fillna(0.00)
            df['prevdayhigh'] = df['prevdayhigh'].fillna(0.00)
            df['prevdaylow'] = df['prevdaylow'].fillna(0.00)
            df['float'] = df['prevdayclose'].fillna(0)

            total_wins = sum(df.profit > 0)
            total_loss = sum(df.profit < 0)
            profits_amount = round(sum(df.loc[df['profit'] > 0].profit), 2)
            losses_amount = round(sum(df.loc[df['profit'] < 0].profit), 2)
            total_rows = df.shape[0]  # gives number of row count
            win_avg_rate = round(((total_wins / total_rows) * 100), 2)
            loss_avg_rate = round(((total_loss / total_rows) * 100), 2)
            avg_per_loss = round((losses_amount / total_rows), 2)
            avg_per_gain = round((profits_amount / total_rows), 2)
            avg_inv_amount = round(df.equity.sum() / total_rows, 2)

            df['entrydate'] = df.entrydate.dt.strftime('%m/%d/%y %H:%M:%S')
            df['exitdate'] = df.exitdate.dt.strftime('%m/%d/%y %H:%M:%S')

            df['entrydate'] = df['entrydate'].astype(str)
            df['exitdate'] = df['exitdate'].astype(str)

            # dictlogs = df.to_json(orient='index')

            dictlogs = df.to_json(orient='split')

            my_trades_dict = {'win_avg_rate': win_avg_rate, 'loss_avg_rate': loss_avg_rate,
                              'total_wins': total_wins, 'total_loss': total_loss, 'total': total_rows,
                              'trade_profit': profits_amount, 'trade_losses': losses_amount,
                              'total_pl': round(df["cummpl"].iloc[-1], 2),
                              'avg_gain': avg_per_gain, 'avg_loss': avg_per_loss, 'avg_inv_amount': avg_inv_amount}

            return HttpResponse(dictlogs, content_type='application/json')

    except Exception as e:
        print(str(e), 'Loading search_filter.')


# Create your views here.
def log(request):
    try:
        df = pd.DataFrame(list(TickerLogger.objects.order_by('-entrydate').values()))

        df['profit'] = (df.exitprice * df.position) - (df.entryprice * df.position)
        df['cummpl'] = df.profit.cumsum()
        df['percentage'] = (((df.exitprice - df.entryprice) / df.entryprice) * 100)
        df['gapentry'] = (((df.entryprice - df.prevdayclose) / df.prevdayclose) * 100)
        df['equity'] = (df.entryprice * df.position)
        df['exitvalue'] = round((df.exitprice * df.position), 2)
        df['prevdayclose'] = df['prevdayclose'].fillna(0.00)
        df['prevdayhigh'] = df['prevdayhigh'].fillna(0.00)
        df['prevdaylow'] = df['prevdaylow'].fillna(0.00)
        df['float'] = df['prevdayclose'].fillna(0)

        total_wins = sum(df.profit > 0)
        total_loss = sum(df.profit < 0)
        profits_amount = round(sum(df.loc[df['profit'] > 0].profit), 2)
        losses_amount = round(sum(df.loc[df['profit'] < 0].profit), 2)
        total_rows = df.shape[0]  # gives number of row count
        win_avg_rate = round(((total_wins / total_rows) * 100), 2)
        loss_avg_rate = round(((total_loss / total_rows) * 100), 2)
        avg_per_loss = round((losses_amount / total_rows), 2)
        avg_per_gain = round((profits_amount / total_rows), 2)
        avg_inv_amount = round(df.equity.sum() / total_rows, 2)

        my_trades_dict = {'win_avg_rate': win_avg_rate, 'loss_avg_rate': loss_avg_rate,
                          'total_wins': total_wins, 'total_loss': total_loss, 'total': total_rows,
                          'trade_profit': profits_amount, 'trade_losses': losses_amount,
                          'total_pl': round(df["cummpl"].iloc[-1], 2),
                          'avg_gain': avg_per_gain, 'avg_loss': avg_per_loss, 'avg_inv_amount': avg_inv_amount}

        dict = df.to_dict(orient='records')

        strategies = list(TickerLogger.objects.values('strategy').distinct().order_by('strategy'))
        myindustries = list(TickerLogger.objects.values('industry').distinct().order_by('industry'))
        mycategories = list(TickerLogger.objects.values('category').distinct().order_by('category'))

        context = {
            'logs': dict,
            'avgwin': win_avg_rate,
            'trades': my_trades_dict,
            'strategies': strategies,
            'industries': myindustries,
            'categories': mycategories

        }

        return render(request, 'blog/log.html', context)
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        print("Too many redirects")
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        print("Too many redirects")
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print(str(e), 'Request Exception.')
        # sys.exit(1)
    except Exception as e:
        print(str(e), ' Log Error')

    return render(request, 'blog/log.html')
