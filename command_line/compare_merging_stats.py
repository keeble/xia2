from __future__ import absolute_import, division, print_function

import math
import os
import sys

import iotbx.merging_statistics
import iotbx.phil
from cctbx import uctbx
from dials.util.options import OptionParser

help_message = """
"""

phil_scope = iotbx.phil.parse(
    """
n_bins = 20
  .type = int(value_min=1)
anomalous = False
  .type = bool
use_internal_variance = False
  .type = bool
eliminate_sys_absent = False
  .type = bool
plot_labels = None
  .type = strings
data_labels = None
  .type = str
size_inches = None
  .type = floats(size=2, value_min=0)
image_dir = None
  .type = path
format = *png pdf
  .type = choice
style = *ggplot
  .type = choice
space_group = None
  .type = space_group
d_min = None
  .type = float
d_max = None
  .type = float
small_multiples = False
  .type = bool
""",
    process_includes=True,
)


def run(args):
    usage = "xia2.compare_merging_stats [options]"

    parser = OptionParser(
        usage=usage, phil=phil_scope, check_format=False, epilog=help_message
    )

    params, options, args = parser.parse_args(
        args, show_diff_phil=True, return_unhandled=True
    )

    results = []
    for mtz in args:
        print(mtz)
        assert os.path.isfile(mtz), mtz
        results.append(
            get_merging_stats(
                mtz,
                anomalous=params.anomalous,
                n_bins=params.n_bins,
                use_internal_variance=params.use_internal_variance,
                eliminate_sys_absent=params.eliminate_sys_absent,
                data_labels=params.data_labels,
                space_group_info=params.space_group,
                d_min=params.d_min,
                d_max=params.d_max,
            )
        )
    plot_merging_stats(
        results,
        labels=params.plot_labels,
        size_inches=params.size_inches,
        image_dir=params.image_dir,
        format=params.format,
        style=params.style,
        small_multiples=params.small_multiples,
    )


def get_merging_stats(
    scaled_unmerged_mtz,
    anomalous=False,
    n_bins=20,
    use_internal_variance=False,
    eliminate_sys_absent=False,
    data_labels=None,
    space_group_info=None,
    d_min=None,
    d_max=None,
):
    i_obs = iotbx.merging_statistics.select_data(
        scaled_unmerged_mtz, data_labels=data_labels
    )
    i_obs = i_obs.customized_copy(anomalous_flag=False, info=i_obs.info())
    if space_group_info is not None:
        i_obs = i_obs.customized_copy(
            space_group_info=space_group_info, info=i_obs.info()
        )
    result = iotbx.merging_statistics.dataset_statistics(
        i_obs=i_obs,
        n_bins=n_bins,
        anomalous=anomalous,
        use_internal_variance=use_internal_variance,
        eliminate_sys_absent=eliminate_sys_absent,
        d_min=d_min,
        d_max=d_max,
    )
    return result


def plot_merging_stats(
    results,
    labels=None,
    plots=None,
    size_inches=None,
    image_dir=None,
    format="png",
    style="ggplot",
    small_multiples=False,
):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    if style is not None:
        plt.style.use(style)

    from cycler import cycler

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    linestyles = []
    for style in ("-", "--", ":", "-."):
        linestyles.extend([style] * len(colors))
    colors = colors * len(set(linestyles))
    plt.rc("axes", prop_cycle=(cycler("c", colors) + cycler("ls", linestyles)))

    plots_ = {
        "r_merge": "$R_{merge}$",
        "r_meas": "$R_{meas}$",
        "r_pim": "$R_{pim}$",
        "cc_one_half": r"$CC_{\frac{1}{2}}$",
        "cc_one_half_sigma_tau": r"$CC_{\frac{1}{2}}$",
        "cc_anom": "$CC_{anom}$",
        "i_over_sigma_mean": r"$< I / \sigma(I) >$",
        "completeness": "Completeness",
        "mean_redundancy": "Multiplicity",
    }

    if plots is None:
        plots = plots_
    else:
        plots = {k: plots_[k] for k in plots}
    if labels is not None:
        assert len(results) == len(labels)
    if image_dir is None:
        image_dir = "."
    elif not os.path.exists(image_dir):
        os.makedirs(image_dir)
    for k in plots:

        n_rows = 1
        n_cols = 1
        if small_multiples:
            n_rows = int(math.floor(math.sqrt(len(results))))
            n_cols = n_rows
            while n_cols * n_rows < len(results):
                n_cols += 1
            assert n_cols * n_rows >= len(results), (n_cols, n_rows, len(results))

        plot_data(results, k, plots.get(k, k), labels, n_rows=n_rows, n_cols=n_cols)

        if size_inches is not None:
            fig = plt.gcf()
            fig.set_size_inches(size_inches)
        if n_cols == 1 and labels is not None:
            if k.startswith("cc"):
                plt.legend(loc="lower left")
            elif k.startswith("r_"):
                plt.legend(loc="upper left")
            elif k.startswith("i_"):
                plt.legend(loc="upper right")
            else:
                plt.legend(loc="best")
        plt.tight_layout()
        plt.savefig(os.path.join(image_dir, k + ".%s" % format))
        plt.clf()


def plot_data(results, k, ylabel, labels, linestyle=None, n_rows=None, n_cols=None):
    from matplotlib import pyplot as plt

    ref_ax = None
    for i, result in enumerate(results):
        if labels is not None:
            label = labels[i].replace("\\$", "$")
        else:
            label = None
        if n_cols > 1:
            ax = plt.subplot(n_rows, n_cols, i + 1, sharex=ref_ax, sharey=ref_ax)
            if label:
                ax.set_title(label)
            if ref_ax is None:
                ref_ax = ax
            for other in results:
                bins = other.bins
                x = [bins[j].d_min for j in range(len(bins))]
                x = [uctbx.d_as_d_star_sq(d) for d in x]
                y = [getattr(bins[j], k) for j in range(len(bins))]
                ax.plot(x, y, linestyle="-", color="grey", linewidth=1, alpha=0.3)
        else:
            ax = plt.gca()

        bins = result.bins
        x = [bins[j].d_min for j in range(len(bins))]
        x = [uctbx.d_as_d_star_sq(d) for d in x]
        y = [getattr(bins[j], k) for j in range(len(bins))]
        ax.plot(x, y, label=label, linestyle=linestyle)

        ax.set_xlabel(r"Resolution ($\AA$)")
        ax.set_ylabel(ylabel)
        ax.label_outer()
        if k in ("cc_one_half", "cc_one_half_sigma_tau", "completeness"):
            ax.set_ylim(0, 1.05)
        elif k in ("cc_anom",):
            ax.set_ylim(min(0, ax.get_ylim()[0]), 1.05)
        else:
            ax.set_ylim(0, ax.get_ylim()[1])
        xticks = ax.get_xticks()
        xticks_d = [
            "%.2f" % uctbx.d_star_sq_as_d(ds2) if ds2 > 0 else 0 for ds2 in xticks
        ]
        ax.set_xticklabels(xticks_d)


if __name__ == "__main__":
    run(sys.argv[1:])
