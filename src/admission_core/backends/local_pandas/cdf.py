"""Pandas implementation of the empirical CDF contract."""
from pathlib import Path
from collections import Counter
import pandas as pd
import pyarrow.dataset as ds
from admission_core.ports import BaseCDFPort
from admission_core.cdf_contract import CDF_KEYS, normalize_scores, summarize_counts, validate_cdf
from admission_core.specs.contracts import BLOCK_NAME_MAP


class LocalPandasCDFBackend(BaseCDFPort):
    def compute_cdf(self, raw_dist_sources, output_uri, options=None):
        counts = Counter()
        found = False
        for name, uri in raw_dist_sources.items():
            if not name.startswith("score_distribution") or not uri:
                continue
            found = True
            dataset = ds.dataset(uri, format="parquet")
            names = dataset.schema.names
            excluded = (options or {}).get("excluded_year_labels", {}).get(name, [])
            if excluded and "Nam" not in names:
                raise ValueError("Loại đợt thi cần cột Nam ở nguồn phổ điểm")
            columns = CDF_KEYS if set(CDF_KEYS).issubset(names) else [column for column in names
                if column in {"score_year", "Nam", *BLOCK_NAME_MAP.values()}]
            if excluded and "Nam" not in columns:
                columns = columns + ["Nam"]
            scanner = dataset.scanner(columns=columns, batch_size=25000, use_threads=False,
                                      batch_readahead=1, fragment_readahead=1)
            for batch in scanner.to_batches():
                frame = batch.to_pandas()
                if excluded:
                    frame = frame.loc[~frame.Nam.astype(str).isin(excluded)]
                observations = normalize_scores(frame, name)
                frequencies = observations.groupby(CDF_KEYS).size()
                counts.update(frequencies.to_dict())
        if not found:
            raise FileNotFoundError("Không có nguồn phổ điểm")
        if not counts:
            raise ValueError("Không có quan sát điểm hợp lệ")
        table = pd.DataFrame([(*key, value) for key, value in counts.items()],
                             columns=CDF_KEYS + ["candidate_count"])
        output = summarize_counts(table)
        validate_cdf(output)
        Path(output_uri).parent.mkdir(parents=True, exist_ok=True)
        output.to_parquet(output_uri, index=False)
        return output_uri
