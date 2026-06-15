# why: negative - two __eq__-style structural-equality helpers over different field sets; dunder/equality boilerplate is parallel by nature and the compared attributes carry the meaning.
def points_equal(self, other):
    if not isinstance(other, type(self)):
        return NotImplemented
    if self.x != other.x:
        return False
    if self.y != other.y:
        return False
    if self.z != other.z:
        return False
    return True


def money_equal(self, other):
    if not isinstance(other, type(self)):
        return NotImplemented
    if self.amount != other.amount:
        return False
    if self.currency != other.currency:
        return False
    if self.scale != other.scale:
        return False
    return True
