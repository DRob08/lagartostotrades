from django.shortcuts import render
from django.http import HttpResponse
from .models import Tickers
import bs4 as bs
import pickle
import datetime as dt
import numpy as np
import pandas as pd
import requests
import json
from django.http import JsonResponse
from alpha_vantage.timeseries import TimeSeries
import matplotlib.pyplot as plt
import time
import io
import re
from finviz.screener import Screener
from alpha_vantage.timeseries import TimeSeries
import matplotlib.ticker as mticker
from mpl_finance import candlestick_ohlc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import date2num
from datetime import datetime
from pytz import timezone
import itertools
import warnings

from pandas.tseries.offsets import BDay

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


def get_cookie_crumb(symbol):
    cookie, lines = get_page_data(symbol)
    crumb = split_crumb_store(find_crumb_store(lines))
    # Note: possible \u002F value
    # ,"CrumbStore":{"crumb":"FWP\u002F5EFll3U"
    # FWP\u002F5EFll3U
    #crumb2 = crumb.decode('unicode-escape')

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
    #lines = r.text.encode('utf-8').strip().replace('}', '\n')
    lines = r.content.decode('unicode-escape').strip().replace('}', '\n')
    return cookie, lines.split('\n')


def get_now_epoch():
    # @see https://www.linuxquestions.org/questions/programming-9/python-datetime-to-epoch-4175520007/#post5244109
    return int(time.time())


def avg_true_range( df):
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
            #si.get_live_price(stock)

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

            else:
                ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
                data, meta_data = ts.get_intraday(symbol=stock, interval=intval, outputsize='compact')

                data_min, meta_data_min = ts.get_intraday(symbol=stock, interval='1min', outputsize='compact')

                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

                avg_true_range(data)

                data["AvgTR"].fillna(0, inplace=True)
                data["TrueRange"].fillna(0, inplace=True)

                MM = PPSR(data)

                dict = MM.to_dict('list')

            return JsonResponse(dict)

        except Exception as e:
            print(str(e), 'failed to organize pulled data.')
        except Exception as e:
            print(str(e), 'failed to pull pricing data')

    return HttpResponse("Request method is not a GET")


def graph_data(data, stock):
    fontsizes = itertools.cycle([8, 16, 24, 32])

    fig = plt.figure(facecolor='#07000d')
    ax1 = plt.subplot2grid((1, 1), (0, 0))
    # ax1 = plt.subplot2grid((6, 4), (1, 0), rowspan=6, colspan=4)

    time_format = '%m-%d-%Y %H:%M:%S'

    data = data.iloc[90:]

    data['Date'] = data.index
    data['Date'] = pd.to_datetime(data['Date'])
    data['Date'] = data["Date"].apply(mdates.date2num)

    dates = data["Date"].tolist()
    openp = data["Open"].tolist()
    highp = data["High"].tolist()
    lowp = data["Low"].tolist()
    closep = data["Close"].tolist()
    volume = data["Volume"].tolist()

    x = 0
    y = len(dates)
    ohlc = []

    while x < y:
        append_me = dates[x], openp[x], highp[x], lowp[x], closep[x], volume[x]
        ohlc.append(append_me)
        x += 1

    # candlestick_ohlc(ax1, ohlc)

    candlestick_ohlc(ax1, ohlc, width=.6/(24*60), colorup='#77d879', colordown='#db3f3f')

    for label in ax1.xaxis.get_ticklabels():
        label.set_rotation(90)

    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter(time_format))
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(10))
    # ax1.grid(True)
    # plt.xticks(rotation=45)

    plt.ylabel('Stock Price')
    plt.xlabel('Date Hours:Minutes')
    plt.title(stock)
    # plt.legend()
    # plt.subplots_adjust(left=0.09, bottom=0.20, right=0.94, top=0.90, wspace=0.2, hspace=0)

    plt.savefig('mychart.png')
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
    psr = {'PP':PP, 'R1':R1, 'S1':S1, 'R2':R2, 'S2':S2, 'R3':R3, 'S3':S3, 'VWAP':VWAP}
    PSR = pd.DataFrame(psr)
    data = data.join(PSR)
    return data


def data_calculations(request):
    if request.method == 'GET':

        stock = request.GET['tcker']

        print('Currently Pulling', stock)

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

            ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
            data, meta_data = ts.get_intraday(symbol=stock, interval='1min', outputsize='full')

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

            LL = PPSR(df)

            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

            data['vwap_pandas'] = (data.Volume * (data.High + data.Low) / 2).cumsum() / data.Volume.cumsum()

            v = data.Volume.values
            h = data.High.values
            l = data.Low.values

            data['vwap_numpy'] = np.cumsum(v * (h + l) / 2) / np.cumsum(v)

            # data['vwap_numba'] = vwap()

            MM = PPSR(data)

            dict = LL.to_dict('list')

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

        resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5,sh_curvol_o200&c=1,25,30,49,59,63,65,67')

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
        resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5,sh_curvol_o200&c=1,25,30,59,63,67,65')
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

    # resp = requests.get('https://finviz.com/')  # soup = bs.BeautifulSoup(resp.text, 'lxml')  html.parser
    resp = requests.get('https://finviz.com/screener.ashx?' + url_screener)
    soup = bs.BeautifulSoup(resp.text, 'lxml')

    columns = []
    for td in soup.find_all("td", class_="table-top"):
        columns.append(td.text.strip())

    columns.insert(1, soup.find("td", class_="table-top-s").text.strip())


    # table_other = soup.find(text="Float").find_parent("table")

    table_rows = soup.find_all('tr', class_="table-dark-row-cp")

    res = []
    for tr in table_rows:
        td = tr.find_all('td')
        row = [tr.text.strip() for tr in td if tr.text.strip()]
        if row:
            res.append(row)

    # res.pop(0)
    df = pd.DataFrame(res, columns=columns)

    df.columns = df.columns.str.strip().str.replace(' ', '').str.replace('(', '').str.replace(')', '').str.replace('/', '')

    dict = df.to_dict(orient='list')

    return JsonResponse(dict, safe=False)


def home(request):
    # ts = TimeSeries(key='G3AXVEKKRY7RYJUD', output_format='pandas')
    # data, meta_data = ts.get_intraday(symbol='NBEV',interval='1min', outputsize='full')
    # data['4. close'].plot()
    # plt.title('Intraday Times Series for the MSFT stock (1 min)')
    # plt.show()

    df_finviz = load_finviz()

    json = df_finviz.to_json()

    # dict = df_finviz.to_dict('list')

    df_finviz['Float'] = df_finviz['Float'].str[:-1]

    df_finviz[["Float"]] = df_finviz[["Float"]].apply(pd.to_numeric)

    df_finviz[["Price"]] = df_finviz[["Price"]].apply(pd.to_numeric)

    df_finviz.sort_values(by=['Price'], inplace=True, ascending=True)

    dict = df_finviz.to_dict(orient='records')

    context = {
        'tickers': Tickers.objects.all(),
        'data': df_finviz.to_html(),
        'symbols': dict

    }
    return render(request, 'blog/home.html', context)


def about(request):
    return render(request, 'blog/about.html', {'title':'About'})


