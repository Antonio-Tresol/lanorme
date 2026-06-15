# why: positive - two ETL transforms copy-pasted then drifted by one removed filtering statement and a changed attribute; reviewer would extract a shared transform helper.
def transform_sales_rows(rows):
    frame = load_into_frame(rows)
    frame = frame.dropna()
    frame = frame.sort_values("date")
    frame = frame[frame.amount > 0]
    frame = frame.reset_index()
    return frame.to_records()


def transform_refund_rows(rows):
    frame = load_into_frame(rows)
    frame = frame.dropna()
    frame = frame.sort_values("date")
    frame = frame.reset_index()
    return frame.to_records()
