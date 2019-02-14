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

def PPSR2(data):

    PP = pd.Series((data['high'] + data['low'] + data['close']) / 3)
    R1 = pd.Series(2 * PP - data['low'])
    S1 = pd.Series(2 * PP - data['high'])
    R2 = pd.Series(PP + data['high'] - data['low'])
    S2 = pd.Series(PP - data['high'] + data['low'])
    R3 = pd.Series(data['high'] + 2 * (PP - data['low']))
    S3 = pd.Series(data['low'] - 2 * (data['high'] - PP))
    psr = {'PP':PP, 'R1':R1, 'S1':S1, 'R2':R2, 'S2':S2, 'R3':R3, 'S3':S3}
    PSR = pd.DataFrame(psr)
    data = data.join(PSR)
    return data


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

        hiredate = '2018-10-28'
        pattern = '%Y-%m-%d'
        epoch_start = int(time.mktime(time.strptime(hiredate, pattern)))

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


def load_finviz():
    # resp = requests.get('https://finviz.com/')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
    resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5&c=1,25,30,49,59,63,65,67')
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


def load_tickers(request):
    if request.method == 'GET':

        # resp = requests.get('https://finviz.com/')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
        resp = requests.get('https://finviz.com/screener.ashx?v=152&s=ta_topgainers&f=sh_price_u5&c=1,25,30,59,63,67,65')  # soup = bs.BeautifulSoup(resp.text, 'lxml')
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


