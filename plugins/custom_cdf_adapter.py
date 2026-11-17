"""Example class adapter implementing the same empirical CDF contract."""
from admission_core.backends.local_pandas.cdf import LocalPandasCDFBackend


class CustomUserCDFAdapter:
    def execute(self, input_uri, output_uri, raw_dist_sources=None, options=None):
        sources = raw_dist_sources or {"score_distribution_ct2006": input_uri}
        return LocalPandasCDFBackend().compute_cdf(sources, output_uri, options)
