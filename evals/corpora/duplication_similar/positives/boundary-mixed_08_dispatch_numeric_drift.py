# why: positive - two scoring loops copy-pasted then drifted by different numeric weights and one extra accumulate statement; reviewer would extract a shared weighted-score helper.
def score_candidate(features):
    total = 0.0
    total += features.skill * 3
    total += features.years * 2
    total += features.referrals * 1
    if features.remote:
        total -= 5
    return round(total, 2)


def score_applicant(features):
    total = 0.0
    total += features.skill * 4
    total += features.years * 2
    total += features.referrals * 2
    total += features.portfolio * 1
    if features.remote:
        total -= 3
    return round(total, 2)
