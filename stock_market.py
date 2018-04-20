import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.externals import joblib
from os.path import isfile
from matplotlib.collections import LineCollection
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode
from sklearn import cluster, covariance, manifold

API_KEY = 'TAEUOVZJR0FV9KLR'
ALPHA_URL = 'https://www.alphavantage.co/query'


def retry(f, n_attempts=3):
    "Wrapper function to retry function calls in case of exceptions"

    def wrapper(*args, **kwargs):
        for i in range(n_attempts):
            try:
                return f(*args, **kwargs)
            except Exception:
                if i == n_attempts - 1:
                    raise

    return wrapper


def quotes_historical_alphavantage(symbol):
    params = {
        'symbol': symbol,
        'datatype': 'csv',
        'interval': '15min',
        'function': 'TIME_SERIES_INTRADAY',
        'apikey': API_KEY
    }
    url = '{url}?{params}'.format(url=ALPHA_URL, params=urlencode(params))
    response = urlopen(url)
    dtype = {
        'names': ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
        'formats': ['object', 'f4', 'f4', 'f4', 'f4', 'f4']
    }
    data = np.genfromtxt(response, delimiter=',', skip_header=1,
                         dtype=dtype,
                         missing_values='-', filling_values=-1)
    # min_date = min(data['timestamp'], default=datetime.min.date())
    # max_date = max(data['timestamp'], default=datetime.max.date())
    df = pd.DataFrame(data)
    return df


symbol_dict = {
    'NYSE:TOT': 'Total',
    'NYSE:XOM': 'Exxon',
    'NYSE:CVX': 'Chevron',
    'NYSE:COP': 'ConocoPhillips',
    'NYSE:VLO': 'Valero Energy',
    'NASDAQ:MSFT': 'Microsoft',
    'NYSE:IBM': 'IBM',
    'NYSE:TWX': 'Time Warner',
    'NASDAQ:CMCSA': 'Comcast',
    'NYSE:CVC': 'Cablevision',
    # 'NASDAQ:YHOO': 'Yahoo',
    # 'NASDAQ:DELL': 'Dell',
    'NYSE:HPQ': 'HP',
    # 'NASDAQ:AMZN': 'Amazon',
    'NYSE:TM': 'Toyota',
    'NYSE:CAJ': 'Canon',
    'NYSE:SNE': 'Sony',
    'NYSE:F': 'Ford',
    'NYSE:HMC': 'Honda',
    'NYSE:NAV': 'Navistar',
    'NYSE:NOC': 'Northrop Grumman',
    'NYSE:BA': 'Boeing',
    'NYSE:KO': 'Coca Cola',
    'NYSE:MMM': '3M',
    'NYSE:MCD': 'McDonald\'s',
    'NYSE:PEP': 'Pepsi',
    'NYSE:K': 'Kellogg',
    'NYSE:UN': 'Unilever',
    # 'NASDAQ:MAR': 'Marriott',
    'NYSE:PG': 'Procter Gamble',
    'NYSE:CL': 'Colgate-Palmolive',
    'NYSE:GE': 'General Electrics',
    'NYSE:WFC': 'Wells Fargo',
    'NYSE:JPM': 'JPMorgan Chase',
    'NYSE:AIG': 'AIG',
    'NYSE:AXP': 'American express',
    'NYSE:BAC': 'Bank of America',
    'NYSE:GS': 'Goldman Sachs',
    # 'NASDAQ:AAPL': 'Apple',
    'NYSE:SAP': 'SAP',
    # 'NASDAQ:CSCO': 'Cisco',
    # 'NASDAQ:TXN': 'Texas Instruments',
    'NYSE:XRX': 'Xerox',
    'NYSE:WMT': 'Wal-Mart',
    'NYSE:HD': 'Home Depot',
    'NYSE:GSK': 'GlaxoSmithKline',
    'NYSE:PFE': 'Pfizer',
    'NYSE:SNY': 'Sanofi-Aventis',
    'NYSE:NVS': 'Novartis',
    'NYSE:KMB': 'Kimberly-Clark',
    'NYSE:R': 'Ryder',
    'NYSE:GD': 'General Dynamics',
    'NYSE:RTN': 'Raytheon',
    'NYSE:CVS': 'CVS',
    'NYSE:CAT': 'Caterpillar',
    'NYSE:DD': 'DuPont de Nemours'
}

symbols, names = np.array(sorted(symbol_dict.items())).T

# retry is used because quotes_historical_google can temporarily fail
# for various reasons (e.g. empty result from Google API).
quotes = []

for symbol in symbols:
    try:
        print('Fetching quote history for %r' % symbol, file=sys.stderr)
        quotes.append(retry(quotes_historical_alphavantage)(symbol))
    except ValueError as e:
        print('Passing {} symbol due to unhandeling api'.format(symbol))
        pass

close_prices = np.vstack([q['close'] for q in quotes])
open_prices = np.vstack([q['open'] for q in quotes])

# The daily variations of the quotes are what carry most information
variation = close_prices - open_prices

# ##########################################################################
# Learn a graphical structure from the correlations
filename = 'model.pkl'
if isfile(filename):
    edge_model = joblib.load(filename)
else:
    edge_model = covariance.GraphLassoCV()

# standardize the time series: using correlations rather than covariance
# is more efficient for structure recovery
X = variation.copy().T
X /= X.std(axis=0)
edge_model.fit(X)

joblib.dump(edge_model, filename)

# ###########################################################################
# Cluster using affinity propagation

_, labels = cluster.affinity_propagation(edge_model.covariance_)
n_labels = labels.max()

# for i in range(n_labels + 1):
#     print('Cluster %i: %s' % ((i + 1), ', '.join(names[labels == i])))

# ###########################################################################
# Find a low-dimension embedding for visualization: find the best position of
# the nodes (the stocks) on a 2D plane

# We use a dense eigen_solver to achieve reproducibility (arpack is
# initiated with random vectors that we don't control). In addition, we
# use a large number of neighbors to capture the large-scale structure.
node_position_model = manifold.LocallyLinearEmbedding(
    n_components=2, eigen_solver='dense', n_neighbors=6)

embedding = node_position_model.fit_transform(X.T).T

# ############################################################################
# Visualization
plt.figure(1, facecolor='w', figsize=(10, 8))
plt.clf()
ax = plt.axes([0., 0., 1., 1.])
plt.axis('off')

# Display a graph of the partial correlations
partial_correlations = edge_model.precision_.copy()
d = 1 / np.sqrt(np.diag(partial_correlations))
partial_correlations *= d
partial_correlations *= d[:, np.newaxis]
non_zero = (np.abs(np.triu(partial_correlations, k=1)) > 0.02)

# Plot the nodes using the coordinates of our embedding
plt.scatter(embedding[0], embedding[1], s=100 * d ** 2, c=labels,
            cmap=plt.cm.spectral)

# Plot the edges
start_idx, end_idx = np.where(non_zero)
# a sequence of (*line0*, *line1*, *line2*), where::
#            linen = (x0, y0), (x1, y1), ... (xm, ym)
segments = [[embedding[:, start], embedding[:, stop]]
            for start, stop in zip(start_idx, end_idx)]
values = np.abs(partial_correlations[non_zero])
lc = LineCollection(segments,
                    zorder=0, cmap=plt.cm.hot_r,
                    norm=plt.Normalize(0, .7 * values.max()))
lc.set_array(values)
lc.set_linewidths(15 * values)
ax.add_collection(lc)

# Add a label to each node. The challenge here is that we want to
# position the labels to avoid overlap with other labels
for index, (name, label, (x, y)) in enumerate(
        zip(names, labels, embedding.T)):

    dx = x - embedding[0]
    dx[index] = 1
    dy = y - embedding[1]
    dy[index] = 1
    this_dx = dx[np.argmin(np.abs(dy))]
    this_dy = dy[np.argmin(np.abs(dx))]
    if this_dx > 0:
        horizontalalignment = 'left'
        x = x + .002
    else:
        horizontalalignment = 'right'
        x = x - .002
    if this_dy > 0:
        verticalalignment = 'bottom'
        y = y + .002
    else:
        verticalalignment = 'top'
        y = y - .002
    plt.text(x, y, name, size=10,
             horizontalalignment=horizontalalignment,
             verticalalignment=verticalalignment,
             bbox=dict(facecolor='w',
                       edgecolor=plt.cm.spectral(label / float(n_labels)),
                       alpha=.6))

plt.xlim(embedding[0].min() - .15 * embedding[0].ptp(),
         embedding[0].max() + .10 * embedding[0].ptp(), )
plt.ylim(embedding[1].min() - .03 * embedding[1].ptp(),
         embedding[1].max() + .03 * embedding[1].ptp())

plt.savefig('result.svg')
plt.show()
