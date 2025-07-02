import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta, date
import requests
from scipy.stats import norm

pd.options.display.float_format = '{:,.4f}'.format

def calcGammaEx(S, K, vol, T, r, q, optType, OI):
    if T == 0 or vol == 0:
        return 0
    dp = (np.log(S/K) + (r - q + 0.5*vol**2)*T) / (vol*np.sqrt(T))
    gamma = np.exp(-q*T) * norm.pdf(dp) / (S * vol * np.sqrt(T))
    return OI * 100 * S * S * 0.01 * gamma

def isThirdFriday(d):
    return d.weekday() == 4 and 15 <= d.day <= 21

def process_index_data(index):
    response = requests.get(f"https://cdn.cboe.com/api/global/delayed_quotes/options/_{index}.json")
    options = response.json()
    spotPrice = options["data"]["close"]
    fromStrike = 0.8 * spotPrice
    toStrike = 1.2 * spotPrice
    todayDate = date.today()
    data_df = pd.DataFrame(options["data"]["options"])

    data_df['CallPut'] = data_df['option'].str.slice(start=-9,stop=-8)
    data_df['ExpirationDate'] = pd.to_datetime(data_df['option'].str.slice(start=-15,stop=-9), format='%y%m%d')
    data_df['Strike'] = data_df['option'].str.slice(start=-8,stop=-3).str.lstrip('0')

    calls = data_df[data_df['CallPut'] == 'C'].reset_index(drop=True)
    puts  = data_df[data_df['CallPut'] == 'P'].reset_index(drop=True)

    df = calls[['ExpirationDate','option','last_trade_price','change','bid','ask','volume','iv','delta','gamma','open_interest','Strike']]
    df_puts = puts[['ExpirationDate','option','last_trade_price','change','bid','ask','volume','iv','delta','gamma','open_interest','Strike']]
    df_puts.columns = ['put_exp','put_option','put_last_trade_price','put_change','put_bid','put_ask','put_volume','put_iv','put_delta','put_gamma','put_open_interest','put_strike']
    df = pd.concat([df, df_puts], axis=1)
    df['check'] = np.where((df['ExpirationDate'] == df['put_exp']) & (df['Strike'] == df['put_strike']), 0, 1)
    if df['check'].sum() != 0:
        raise ValueError("PUT CALL MERGE FAILED - OPTIONS ARE MISMATCHED.")
    df.drop(['put_exp', 'put_strike', 'check'], axis=1, inplace=True)

    df.columns = ['ExpirationDate','Calls','CallLastSale','CallNet','CallBid','CallAsk','CallVol',
                'CallIV','CallDelta','CallGamma','CallOpenInt','StrikePrice','Puts','PutLastSale',
                'PutNet','PutBid','PutAsk','PutVol','PutIV','PutDelta','PutGamma','PutOpenInt']
    df['ExpirationDate'] = pd.to_datetime(df['ExpirationDate']) + timedelta(hours=16)
    df = df.astype({
        'StrikePrice': float,
        'CallIV': float, 'PutIV': float,
        'CallGamma': float, 'PutGamma': float,
        'CallOpenInt': float, 'PutOpenInt': float
    })

    df['CallGEX'] = df['CallGamma'] * df['CallOpenInt'] * 100 * spotPrice**2 * 0.01
    df['PutGEX'] = df['PutGamma'] * df['PutOpenInt'] * 100 * spotPrice**2 * 0.01 * -1
    df['TotalGamma'] = (df.CallGEX + df.PutGEX) / 1e9

    dfAgg = df.groupby(['StrikePrice']).sum(numeric_only=True)
    strikes = dfAgg.index.values
    totalGamma = dfAgg['TotalGamma'].values

    fig, ax = plt.subplots()
    ax.grid()
    ax.bar(strikes, totalGamma, width=6, linewidth=0.1, edgecolor='k', label='Exposição Gama')
    ax.set_xlim([fromStrike, toStrike])
    ax.set_title(f'Total Gamma: ${df["TotalGamma"].sum():.2f} Bn por 1% {index} Move', fontweight='bold', fontsize=16)
    ax.set_xlabel('Strike', fontweight='bold')
    ax.set_ylabel('Exposição Gama ($ bilhões / 1% move)', fontweight='bold')
    ax.axvline(x=spotPrice, color='r', lw=1, label=f"{index} Spot: {spotPrice:.0f}")
    ax.legend()

    return fig
