"""
DCA Frequency Comparison Backtest
Compare different investment frequencies: daily, weekly (Mon-Fri), monthly
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


class FrequencyDCAStrategy(bt.Strategy):
    """DCA with different frequencies"""
    params = (
        ('total_annual_investment', 104000),  # Total annual investment ($2000 * 52 weeks)
        ('gld_pct', 0.50),
        ('qqq_pct', 0.25),
        ('spy_pct', 0.25),
        ('frequency', 'weekly'),  # 'daily', 'weekly_mon', 'weekly_tue', ..., 'monthly'
    )

    def __init__(self):
        self.data_map = {}
        self.last_investment_date = None
        self.total_invested = 0
        self.investment_count = 0

        for data in self.datas:
            name = data._name
            self.data_map[name] = data

        # Calculate per-investment amount based on frequency
        if self.params.frequency == 'daily':
            self.investment_amount = self.params.total_annual_investment / 252  # ~252 trading days
        elif self.params.frequency.startswith('weekly'):
            self.investment_amount = self.params.total_annual_investment / 52
        elif self.params.frequency == 'monthly':
            self.investment_amount = self.params.total_annual_investment / 12
        else:
            self.investment_amount = self.params.total_annual_investment / 52

    def should_invest_today(self, current_date):
        """Check if should invest based on frequency"""
        freq = self.params.frequency
        weekday = current_date.weekday()  # 0=Monday, 4=Friday

        if freq == 'daily':
            return True
        elif freq == 'weekly_mon':
            return weekday == 0
        elif freq == 'weekly_tue':
            return weekday == 1
        elif freq == 'weekly_wed':
            return weekday == 2
        elif freq == 'weekly_thu':
            return weekday == 3
        elif freq == 'weekly_fri':
            return weekday == 4
        elif freq == 'monthly':
            # Invest on first trading day of month
            if self.last_investment_date is None:
                return True
            return current_date.month != self.last_investment_date.month
        else:
            return False

    def next(self):
        current_date = self.datas[0].datetime.date(0)

        if self.should_invest_today(current_date):
            self.broker.add_cash(self.investment_amount)
            self.total_invested += self.investment_amount
            self.investment_count += 1
            self.invest()
            self.last_investment_date = current_date

    def invest(self):
        """Invest according to allocation"""
        investable = self.investment_amount * 0.997

        allocations = [
            ('GLD', self.params.gld_pct),
            ('QQQ', self.params.qqq_pct),
            ('SPY', self.params.spy_pct)
        ]

        for name, pct in allocations:
            if pct > 0 and name in self.data_map:
                data = self.data_map[name]
                invest_amount = investable * pct
                size = invest_amount / data.close[0]

                if size > 0.01:
                    self.buy(data=data, size=size)


def run_frequency_backtest(frequency, start_year=2005):
    """Run backtest with specific frequency"""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1000.0)
    cerebro.broker.setcommission(commission=0.001)

    # Load data
    for name, filename in [('GLD', 'GLD.csv'), ('QQQ', 'QQQ.csv'), ('SPY', 'SPY.csv')]:
        filepath = f'data/{filename}'
        df = pd.read_csv(filepath)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[df['Date'].dt.year >= start_year]

        if len(df) == 0:
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
        FrequencyDCAStrategy,
        frequency=frequency
    )

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    try:
        results = cerebro.run()
        strat = results[0]

        final_value = cerebro.broker.getvalue()
        total_invested = strat.total_invested
        total_profit = final_value - total_invested
        total_return = (total_profit / total_invested) * 100 if total_invested > 0 else 0
        years = 2025 - start_year
        annual_return = total_return / years if years > 0 else 0

        # Get analysis
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
            'frequency': frequency,
            'final_value': final_value,
            'total_invested': total_invested,
            'total_profit': total_profit,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe': sharpe_ratio,
            'max_drawdown': max_dd,
            'investment_count': strat.investment_count,
        }

    except Exception as e:
        print(f'Error: {str(e)}')
        return None


def main():
    print('='*70)
    print('DCA Frequency Comparison (2005-2025)')
    print('Annual Investment: $104,000 (same total for all frequencies)')
    print('='*70)
    print()

    frequencies = [
        ('daily', 'Daily'),
        ('weekly_mon', 'Weekly Monday'),
        ('weekly_tue', 'Weekly Tuesday'),
        ('weekly_wed', 'Weekly Wednesday'),
        ('weekly_thu', 'Weekly Thursday'),
        ('weekly_fri', 'Weekly Friday'),
        ('monthly', 'Monthly'),
    ]

    all_results = []

    for freq_code, freq_name in frequencies:
        print(f'Testing {freq_name}...', end=' ')
        result = run_frequency_backtest(freq_code, 2005)

        if result:
            result['freq_name'] = freq_name
            all_results.append(result)
            print(f'✓ Annual: {result["annual_return"]:.2f}%, '
                  f'Investments: {result["investment_count"]}, '
                  f'Final: ${result["final_value"]/1000000:.2f}M')

    # Save results
    df = pd.DataFrame(all_results)
    df.to_csv('dca_frequency_results.csv', index=False)
    print(f'\n✓ Results saved to dca_frequency_results.csv')

    # Generate report
    generate_report(all_results)
    plot_comparison(df)


def generate_report(all_results):
    """Generate comparison report"""
    print('\n' + '='*70)
    print('Frequency Comparison Report')
    print('='*70)

    # Sort by annual return
    sorted_results = sorted(all_results, key=lambda x: x['annual_return'], reverse=True)

    print('\nRanking by Annual Return:')
    print('-'*70)
    for i, result in enumerate(sorted_results, 1):
        print(f'{i}. {result["freq_name"]:20s}: {result["annual_return"]:.2f}% annual, '
              f'{result["total_return"]:.1f}% total, '
              f'MaxDD {result["max_drawdown"]:.1f}%')

    # Calculate differences
    best = sorted_results[0]
    worst = sorted_results[-1]
    diff = best['annual_return'] - worst['annual_return']

    print('\n' + '-'*70)
    print(f'Best: {best["freq_name"]} ({best["annual_return"]:.2f}%)')
    print(f'Worst: {worst["freq_name"]} ({worst["annual_return"]:.2f}%)')
    print(f'Difference: {diff:.2f}% annual return')
    print(f'20-year profit difference: ${(best["total_profit"] - worst["total_profit"])/1000:.0f}K')


def plot_comparison(df):
    """Generate comparison charts"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('DCA Frequency Comparison (2005-2025, $104K/year)',
                 fontsize=14, fontweight='bold')

    # Sort by annual return for display
    df_sorted = df.sort_values('annual_return', ascending=True)

    # 1. Annual Return
    ax1 = axes[0, 0]
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(df_sorted)))
    bars = ax1.barh(df_sorted['freq_name'], df_sorted['annual_return'], color=colors)
    ax1.set_xlabel('Annual Return (%)', fontweight='bold')
    ax1.set_title('Annual Return by Frequency', fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)

    # Add value labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax1.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                f'{width:.2f}%', va='center', fontweight='bold')

    # 2. Total Profit
    ax2 = axes[0, 1]
    df_sorted_profit = df.sort_values('total_profit', ascending=True)
    bars2 = ax2.barh(df_sorted_profit['freq_name'],
                     df_sorted_profit['total_profit']/1000000, color=colors)
    ax2.set_xlabel('Total Profit ($M)', fontweight='bold')
    ax2.set_title('Total Profit by Frequency', fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)

    for i, bar in enumerate(bars2):
        width = bar.get_width()
        ax2.text(width + 0.05, bar.get_y() + bar.get_height()/2,
                f'${width:.2f}M', va='center', fontweight='bold')

    # 3. Max Drawdown
    ax3 = axes[1, 0]
    df_sorted_dd = df.sort_values('max_drawdown', ascending=False)
    colors_dd = ['#F44336' if x > 24 else '#4CAF50' for x in df_sorted_dd['max_drawdown']]
    bars3 = ax3.barh(df_sorted_dd['freq_name'], df_sorted_dd['max_drawdown'], color=colors_dd)
    ax3.set_xlabel('Max Drawdown (%)', fontweight='bold')
    ax3.set_title('Max Drawdown by Frequency', fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)

    for i, bar in enumerate(bars3):
        width = bar.get_width()
        ax3.text(width + 0.2, bar.get_y() + bar.get_height()/2,
                f'{width:.1f}%', va='center', fontweight='bold')

    # 4. Summary Table
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')

    # Create summary table
    table_data = [
        ['Frequency', 'Annual\nReturn', 'Total\nProfit', 'Max\nDrawdown', 'Invest\nCount']
    ]

    df_table = df.sort_values('annual_return', ascending=False)
    for _, row in df_table.iterrows():
        table_data.append([
            row['freq_name'],
            f'{row["annual_return"]:.2f}%',
            f'${row["total_profit"]/1000000:.2f}M',
            f'{row["max_drawdown"]:.1f}%',
            f'{row["investment_count"]}'
        ])

    table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.25, 0.18, 0.18, 0.18, 0.18])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Style header
    for i in range(5):
        table[(0, i)].set_facecolor('#1976D2')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Highlight best
    for i in range(5):
        table[(1, i)].set_facecolor('#4CAF50')
        table[(1, i)].set_text_props(weight='bold', color='white')

    ax4.set_title('Performance Summary', fontweight='bold', fontsize=12, pad=20)

    plt.tight_layout()
    plt.savefig('dca_frequency_comparison.png', dpi=100, bbox_inches='tight')
    print('✓ Chart saved to dca_frequency_comparison.png')


if __name__ == '__main__':
    main()
