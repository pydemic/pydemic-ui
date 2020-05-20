from collections import namedtuple

import numpy as np
import pandas as pd
from scipy import special as sfn, optimize

from pydemic_ui import st

MeanStd = namedtuple("MeanStd", ("mean", "std"))

r = st.number_input("Growth factor", value=1.2)
N = st.number_input("N", value=50)
alpha = st.number_input("alpha", value=2.0, format="%0.4g")
rng = np.random.default_rng()


# @st.cache
def test_data(r, N, alpha):
    X = np.linspace(0, 10, N)
    R = rng.gamma(alpha, r / alpha, size=N)
    Y = np.multiply.accumulate(R)
    return pd.Series(Y, index=X)


def log_Zk(alpha, Y, approx=False):
    alpha = np.asarray(alpha)
    if not alpha.shape:
        return np.sum(log_Zk(np.array([alpha]), Y, approx))

    eta = (Y[1:] / Y[:-1])[None, :]
    delta = np.log(eta.mean()) - np.log(eta).mean()
    N = len(Y) - 1
    out = -N * alpha * delta
    if approx:
        out += 0.5 * N * np.log(alpha) - N
        return out
    out -= N * alpha * np.log(1 + 1 / (N * alpha * eta.mean()))
    out += sfn.loggamma(N * alpha)
    out -= N * sfn.loggamma(alpha)
    out -= N * alpha * np.log(N)
    return out


data = test_data(r, N, alpha)
Y = data.values


def r_stats(Y):
    """
    Return the (mean, std_deviation) of R from data.
    """
    Y = np.asarray(Y)
    eta = Y[1:] / Y[:-1]
    N = len(eta)
    eta_mean = eta.mean()
    delta = np.log(eta_mean) - np.log(eta).mean()
    mean = (eta_mean + 2 * delta / N) / (1 + 2 * delta / N)
    std = mean * np.sqrt(delta / np.maximum(N / 2 - 2 * delta, 0.0))

    return MeanStd(mean, std)


k = float(optimize.fmin(lambda k: -log_Zk(k, Y), 1))
beta = k
alpha = 1.0 + k
N = len(Y) - 1
eta = Y[1:] / Y[:-1]

K = np.linspace(10, 150, 200)
Zk = log_Zk(K, Y)


def progression(r, x, N):
    out = [x]
    for _ in range(N - 1):
        x *= r
        out.append(x)
    return np.array(out)


mu, sigma = r_stats(data.values)
T = data.index
N = len(T)
x0 = data.iloc[0]
st.line_chart(
    pd.DataFrame(
        {
            "data": np.log(data.values),
            "mean": np.log(progression(mu, x0, N)),
            "high": np.log(progression(mu + sigma, x0, N)),
            "low": np.log(progression(mu - sigma, x0, N)),
        },
        index=T,
    )
)

if st.checkbox("show?"):
    r_mean = mu
    r_sigma = sigma
    r_sigma_rel = r_sigma / r_mean

    st.experimental_show(r_mean)
    st.experimental_show(r_sigma)
    st.experimental_show(r_sigma_rel)

st.line_chart(
    pd.DataFrame(
        {"approx": log_Zk(K, Y, approx=True), "no-approx": log_Zk(K, Y, approx=False)},
        index=K,
    ).dropna()
)
