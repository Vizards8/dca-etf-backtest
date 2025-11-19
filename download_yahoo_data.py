"""
从Yahoo Finance查询接口下载期货数据并转换为CSV格式

数据源说明：
- 使用特定的Yahoo Finance查询URL
- period1: 1100822400 (2004-11-19，固定开始日期)
- period2: 1763101604 (2025-11-14，可修改为最新时间戳)

更新数据：
修改下面URL中的period2参数为最新的Unix时间戳即可获取最新数据。
可以使用 https://www.unixtimestamp.com/ 转换日期为时间戳。

例如：
- 2025-12-31 → 1735689599
- 2026-01-01 → 1735776000
"""

import requests
import pandas as pd
import json
from datetime import datetime
import os
import time

def download_yahoo_data(url, symbol_name):
    """
    从Yahoo Finance API下载数据

    参数:
        url: Yahoo Finance API URL
        symbol_name: 标的名称（用于保存文件）
    """
    try:
        print(f'正在下载 {symbol_name} 数据...')

        # 添加User-Agent和Headers避免被限制
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        # 下载数据，增加重试
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10
                        print(f'  频率限制，等待{wait_time}秒后重试...')
                        time.sleep(wait_time)
                    else:
                        print(f'✗ {symbol_name} 下载失败: 超过重试次数')
                        return None
                else:
                    print(f'✗ {symbol_name} 下载失败: HTTP {response.status_code}')
                    return None

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f'  请求失败，重试中...')
                    time.sleep(5)
                else:
                    raise e

        # 解析JSON
        data = response.json()

        # 提取数据
        chart = data['chart']['result'][0]
        timestamps = chart['timestamp']
        quotes = chart['indicators']['quote'][0]

        # 创建DataFrame
        df = pd.DataFrame({
            'Date': [datetime.fromtimestamp(ts) for ts in timestamps],
            'Open': quotes['open'],
            'High': quotes['high'],
            'Low': quotes['low'],
            'Close': quotes['close'],
            'Volume': quotes['volume'],
        })

        # 添加Adj Close列（期货数据通常没有调整收盘价，使用收盘价）
        df['Adj Close'] = df['Close']

        # 删除空值
        df = df.dropna()

        # 格式化日期
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        print(f'✓ {symbol_name} 数据下载成功：{len(df)}行')
        print(f'  日期范围: {df["Date"].iloc[0]} 至 {df["Date"].iloc[-1]}')

        return df

    except Exception as e:
        print(f'✗ {symbol_name} 下载失败: {str(e)}')
        return None


def save_to_csv(df, filename, data_dir='data'):
    """保存DataFrame为CSV文件"""
    try:
        # 确保data目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        filepath = os.path.join(data_dir, filename)
        df.to_csv(filepath, index=False)

        print(f'✓ 数据已保存: {filepath}')
        return True

    except Exception as e:
        print(f'✗ 保存失败: {str(e)}')
        return False


def main():
    print('='*70)
    print('Yahoo Finance 期货数据下载工具')
    print('='*70)
    print()

    # 数据源配置
    data_sources = [
        {
            'url': 'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?events=capitalGain%7Cdiv%7Csplit&formatted=true&includeAdjustedClose=true&interval=1d&period1=1100822400&period2=1763101604&symbol=GC%3DF&userYfid=true',
            'name': '黄金期货 (GC=F)',
            'filename': 'GLD.csv'
        },
        {
            'url': 'https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?events=capitalGain%7Cdiv%7Csplit&formatted=true&includeAdjustedClose=true&interval=1d&period1=1100822400&period2=1763101604&symbol=NQ%3DF&userYfid=true',
            'name': '纳斯达克100期货 (NQ=F)',
            'filename': 'QQQ.csv'
        },
        {
            'url': 'https://query1.finance.yahoo.com/v8/finance/chart/ES=F?events=capitalGain%7Cdiv%7Csplit&formatted=true&includeAdjustedClose=true&interval=1d&period1=1100822400&period2=1763101604&symbol=ES%3DF&userYfid=true',
            'name': '标普500期货 (ES=F)',
            'filename': 'SPY.csv'
        },
        {
            'url': 'https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?events=capitalGain%7Cdiv%7Csplit&formatted=true&includeAdjustedClose=true&interval=1d&period1=1100822400&period2=1763467742&symbol=%5EVIX&userYfid=true&lang=en-US&region=US',
            'name': 'VIX恐慌指数 (^VIX)',
            'filename': 'VIX.csv'
        }
    ]

    success_count = 0

    # 下载所有数据
    for i, source in enumerate(data_sources):
        df = download_yahoo_data(source['url'], source['name'])

        if df is not None:
            if save_to_csv(df, source['filename']):
                success_count += 1

        print()

        # 在请求之间添加延迟，避免被限制
        if i < len(data_sources) - 1:
            wait_time = 5
            print(f'等待{wait_time}秒后下载下一个数据集...')
            time.sleep(wait_time)
            print()

    # 总结
    print('='*70)
    print('下载完成')
    print('='*70)
    print(f'成功: {success_count}/{len(data_sources)}')
    print()

    if success_count == len(data_sources):
        print('✓ 所有数据下载成功！')
        print()
        print('下一步：运行回测')
        print('  python dca_backtest.py')
    elif success_count > 0:
        print('⚠ 部分数据下载成功')
        print()
        print('已下载的数据可以用于回测')
    else:
        print('✗ 所有数据下载失败')
        print()
        print('可能的原因：')
        print('1. Yahoo Finance API频率限制')
        print('2. 网络连接问题')
        print()
        print('备选方案：')
        print('1. 等待一段时间后重试')
        print('2. 在浏览器中打开URL并手动保存JSON，然后使用 convert_json_to_csv.py 转换')


if __name__ == '__main__':
    main()
