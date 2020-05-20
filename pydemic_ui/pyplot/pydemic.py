import matplotlib.pyplot as plt
import pandas as pd

from ..i18n import _


def cases_and_deaths(
    data,
    logy=False,
    grid=False,
    dates=False,
    ax: plt.Axes = None,
    smooth=True,
    cases="cases",
    deaths="deaths",
) -> plt.Axes:
    """
    A simple chart showing observed new cases cases as vertical bars and
    a smoothed out prediction of this curve.
    """

    if not dates:
        data = data.reset_index(drop=True)

    # Smoothed data
    col_names = {cases: _("Cases"), deaths: _("Deaths")}
    if smooth:
        from pydemic import fitting as fit

        smooth = pd.DataFrame(
            {
                _("{} (smooth)").format(col_names[cases]): fit.smoothed_diff(data[cases]),
                _("{} (smooth)").format(col_names[deaths]): fit.smoothed_diff(
                    data[deaths]
                ),
            },
            index=data.index,
        )
        ax = smooth.plot(legend=False, lw=2, logy=logy, ax=ax)

    # Prepare cases dataframe and plot it
    new_cases = data.diff().fillna(0)
    new_cases = new_cases.rename(col_names, axis=1)
    ax: plt.Axes = new_cases.plot.bar(width=1.0, alpha=0.5, grid=grid, logy=logy, ax=ax)

    # Fix xticks
    periods = 7 if dates else 10
    xticks = ax.get_xticks()
    labels = ax.get_xticklabels()
    ax.set_xticks(xticks[::periods])
    ax.set_xticklabels(labels[::periods])
    ax.tick_params("x", rotation=0)
    ax.set_ylim(1, None)
    return ax
