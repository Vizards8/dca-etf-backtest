"""
Dollar-Cost Averaging (DCA) Backtest
Weekly investment with Buy & Hold strategy
"""
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configure matplotlib
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


class DCAStrategy(bt.Strategy):
    """Weekly DCA with Buy & Hold strategy"""
    params = (
        ('weekly_investment', 2000),
        ('gld_pct', 0.50),  # 50% Gold
        ('qqq_pct', 0.25),  # 25% QQQ
        ('spy_pct', 0.25),  # 25% SPY
    )

    def __init__(self):
        self.data_map = {}
        self.last_investment_date = None
        self.total_invested = 0

        for data in self.datas:
            name = data._name
            self.data_map[name] = data

    def next(self):
        current_date = self.datas[0].datetime.date(0)

        # Weekly investment: check if 7 days passed
        if self.last_investment_date is None or \
           (current_date - self.last_investment_date).days >= 7:

            self.broker.add_cash(self.params.weekly_investment)
            self.total_invested += self.params.weekly_investment
            self.invest_weekly()
            self.last_investment_date = current_date

    def invest_weekly(self):
        """Invest according to allocation ratio and hold"""
        weekly_amount = self.params.weekly_investment * 0.997  # Reserve for commission

        allocations = [
            ('GLD', self.params.gld_pct),
            ('QQQ', self.params.qqq_pct),
            ('SPY', self.params.spy_pct)
        ]

        for name, pct in allocations:
            if pct > 0 and name in self.data_map:
                data = self.data_map[name]
                invest_amount = weekly_amount * pct
                size = invest_amount / data.close[0]

                if size > 0.01:
                    self.buy(data=data, size=size)


def run_backtest(start_year=2005, weekly_investment=2000):
    """Run DCA backtest"""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(weekly_investment)  # Initial capital = 1 week investment
    cerebro.broker.setcommission(commission=0.001)

    # Load data
    for name, filename in [('GLD', 'GLD.csv'), ('QQQ', 'QQQ.csv'), ('SPY', 'SPY.csv')]:
        filepath = f'data/{filename}'
        df = pd.read_csv(filepath)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[df['Date'].dt.year >= start_year]

        if len(df) == 0:
            print(f'No data available for {name} starting from {start_year}')
            return None

        df = df.set_index('Date')

        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,
            open='Open',
            high='High',
            low='Low',
            close='Close',
            volume='Volume',
            openinterest=-1
        )
        cerebro.adddata(data, name=name)

    # Add strategy
    cerebro.addstrategy(
        DCAStrategy,
        weekly_investment=weekly_investment
    )

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    try:
        results = cerebro.run()
        strat = results[0]

        final_value = cerebro.broker.getvalue()
        years = 2025 - start_year
        total_invested = weekly_investment + weekly_investment * 52 * (years - 1/52)
        total_profit = final_value - total_invested
        total_return = (total_profit / total_invested) * 100
        annual_return = total_return / years if years > 0 else 0

        # Get analysis results
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()

        try:
            max_dd = drawdown.max.drawdown if hasattr(drawdown, 'max') and hasattr(drawdown.max, 'drawdown') else 0
        except:
            max_dd = 0

        try:
            sharpe_ratio = sharpe.get('sharperatio', 0) if sharpe else 0
        except:
            sharpe_ratio = 0

        return {
            'start_year': start_year,
            'final_value': final_value,
            'total_invested': total_invested,
            'total_profit': total_profit,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe': sharpe_ratio,
            'max_drawdown': max_dd,
            'years': years,
        }
    except Exception as e:
        print(f'Error: {str(e)}')
        return None


def main():
    print('='*70)
    print('Dollar-Cost Averaging Backtest')
    print('Weekly Investment: $2,000')
    print('Allocation: 50% GLD, 25% QQQ, 25% SPY')
    print('Strategy: Buy & Hold')
    print('='*70)

    # Test different start years
    start_years = [2005, 2008, 2010, 2015, 2020]
    all_results = []

    for start_year in start_years:
        print(f'\nTesting start year: {start_year}...', end=' ')
        result = run_backtest(start_year, 2000)

        if result:
            all_results.append(result)
            print(f'✓ Annual Return: {result["annual_return"]:.2f}%, '
                  f'Total Return: {result["total_return"]:.1f}%, '
                  f'Max Drawdown: {result["max_drawdown"]:.1f}%')

    # Save results
    df = pd.DataFrame(all_results)
    df.to_csv('dca_backtest_results.csv', index=False)
    print(f'\n✓ Results saved to dca_backtest_results.csv')

    # Generate report
    print('\n' + '='*70)
    print('Performance Summary')
    print('='*70)
    print(f'Average Annual Return: {df["annual_return"].mean():.2f}%')
    print(f'Best Performance: {df["annual_return"].max():.2f}% (Start {df.loc[df["annual_return"].idxmax(), "start_year"]:.0f})')
    print(f'Worst Performance: {df["annual_return"].min():.2f}% (Start {df.loc[df["annual_return"].idxmin(), "start_year"]:.0f})')
    print(f'Average Max Drawdown: {df["max_drawdown"].mean():.2f}%')

    # Generate chart
    plot_results(df)


def plot_results(df):
    """Generate performance chart"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('DCA Performance: Weekly $2000 (50% GLD, 25% QQQ, 25% SPY)',
                 fontsize=14, fontweight='bold')

    # 1. Final value by start year
    ax1 = axes[0, 0]
    colors = ['#2E7D32' if x >= 15 else '#F57C00' for x in df['annual_return']]
    ax1.bar(df['start_year'].astype(str), df['final_value']/1000, color=colors)
    ax1.set_xlabel('Start Year', fontweight='bold')
    ax1.set_ylabel('Final Value ($1000s)', fontweight='bold')
    ax1.set_title('Final Portfolio Value', fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for i, (year, value) in enumerate(zip(df['start_year'], df['final_value'])):
        ax1.text(i, value/1000, f'${value/1000000:.1f}M',
                ha='center', va='bottom', fontweight='bold')

    # 2. Annual return by start year
    ax2 = axes[0, 1]
    ax2.plot(df['start_year'], df['annual_return'],
            marker='o', linewidth=2, markersize=8, color='#1976D2')
    ax2.set_xlabel('Start Year', fontweight='bold')
    ax2.set_ylabel('Annual Return (%)', fontweight='bold')
    ax2.set_title('Annual Return by Start Year', fontweight='bold')
    ax2.grid(alpha=0.3)
    ax2.axhline(y=df['annual_return'].mean(), color='red',
               linestyle='--', alpha=0.5, label=f'Average {df["annual_return"].mean():.1f}%')
    ax2.legend()

    # 3. Investment vs profit
    ax3 = axes[1, 0]
    x = np.arange(len(df))
    width = 0.35
    ax3.bar(x - width/2, df['total_invested']/1000, width,
           label='Total Invested', color='#FFA726')
    ax3.bar(x + width/2, df['total_profit']/1000, width,
           label='Profit', color='#66BB6A')
    ax3.set_xlabel('Start Year', fontweight='bold')
    ax3.set_ylabel('Amount ($1000s)', fontweight='bold')
    ax3.set_title('Investment vs Profit', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(df['start_year'].astype(str))
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)

    # 4. Performance summary table
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')

    table_data = [
        ['Start Year', 'Annual\nReturn', 'Total\nReturn', 'Max\nDrawdown', 'Total\nInvested']
    ]

    for _, row in df.iterrows():
        table_data.append([
            f'{row["start_year"]:.0f}',
            f'{row["annual_return"]:.2f}%',
            f'{row["total_return"]:.1f}%',
            f'{row["max_drawdown"]:.1f}%',
            f'${row["total_invested"]/1000000:.2f}M'
        ])

    table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.2, 0.2, 0.2, 0.2, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Style header row
    for i in range(5):
        table[(0, i)].set_facecolor('#1976D2')
        table[(0, i)].set_text_props(weight='bold', color='white')

    ax4.set_title('Performance by Start Year', fontweight='bold', fontsize=12, pad=20)

    plt.tight_layout()
    plt.savefig('dca_backtest_results.png', dpi=100, bbox_inches='tight')
    print('✓ Chart saved to dca_backtest_results.png')


if __name__ == '__main__':
    main()
