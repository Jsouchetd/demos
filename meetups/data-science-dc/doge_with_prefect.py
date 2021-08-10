import requests as re
import pandas as pd
from datetime import datetime, timedelta
from prefect.tasks.control_flow.case import case

from prefect import task, Flow, Parameter, unmapped
from prefect.tasks.notifications import SlackTask


def format_url(coin="DOGE"):
    url = "https://production.api.coindesk.com/v2/price/values/"
    start_time = (datetime.now() - timedelta(minutes=10)).isoformat(timespec="minutes")
    end_time = datetime.now().isoformat(timespec="minutes")
    params = f"?start_date={start_time}&end_date={end_time}&ohlc=false"
    return url + coin + params

@task(max_retries = 3, retry_delay=timedelta(minutes=1))
def get_data(coin="DOGE") -> pd.DataFrame:
    prices = re.get(format_url(coin))
    prices = prices.json()['data']['entries']
    data = pd.DataFrame(prices, columns=["time", "price"])
    return data

@task
def detect_dip(df: pd.DataFrame, threshold):
    peak = df['price'].max()
    bottom = df['price'].min()
    dip = 100 - (bottom/peak)*100
    
    if dip > threshold:
        return True
    else:
        return False

@task
def reduce_dips(dips):
    return max(dips)

post_to_slack = SlackTask(message="There has been a dip in DOGE price.", webhook_secret="SLACK_WEBHOOK_URL")

with Flow("to-the-moon") as flow:
    coin = Parameter("coin", default="DOGE")
    threshold = Parameter("threshold", default=0)
    data = get_data(coin)
    is_dip = detect_dip(data, threshold=threshold)
    with case(is_dip, True):
        post_to_slack()

flow.register("dsdc")